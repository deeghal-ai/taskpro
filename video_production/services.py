"""
Video Production Service Layer - mirrors projects/services.py
Handles business logic for video production management.
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, Subquery, OuterRef, F, Prefetch
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import datetime, date, timedelta
import re

from .models import (
    VideoProject, VideoProjectStatusOption, VideoProjectStatusHistory, 
    VideoProjectDelivery, VideoProduct
)
from locations.models import City

logger = logging.getLogger(__name__)

User = get_user_model()

class VideoProjectService:
    """
    Service class for video project operations - mirrors ProjectService from projects app.
    Handles CRUD operations, status management, and business logic.
    """
    
    @staticmethod
    def create_video_project(project_data, user):
        """
        Creates a new video project with proper validation and business logic.
        Works with data from any source (forms, API, CLI).
        Mirrors projects service implementation exactly.
        
        Args:
            project_data: Dictionary with project data
            user: User creating the project (must be VIDEO_PM)
        
        Returns:
            tuple: (success, result)
                - If successful: (True, project)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                # Get initial status
                initial_status = VideoProjectStatusOption.objects.filter(
                    is_active=True
                ).order_by('order').first()
                
                if not initial_status:
                    return False, "No active status options found. Please create status options first."
                
                # Create project object from validated data  
                project = VideoProject(
                    opportunity_id=project_data['opportunity_id'],
                    project_name=project_data['project_name'],
                    builder_name=project_data['builder_name'],
                    city=project_data['city'],
                    product=project_data['product'],
                    package_id=project_data.get('package_id'),
                    quantity=project_data['quantity'],
                    purchase_date=project_data['purchase_date'],
                    sales_confirmation_date=project_data['sales_confirmation_date'],
                    account_manager=project_data['account_manager'],
                    current_status=initial_status,
                    video_pm=user,
                    project_type=project_data.get('project_type') or None
                )
                
                # Set expected TAT from the product if not specified
                if not project_data.get('expected_tat'):
                    project.expected_tat = project.product.expected_tat
                else:
                    project.expected_tat = project_data['expected_tat']
                
                # Generate HS_ID explicitly before saving
                project.hs_id = VideoProject.generate_hs_id()
                
                # Set user and skip automatic status history creation since we'll create specific ones
                project._current_user = user
                project._skip_status_history = True  # Skip automatic creation
                
                # Validate and save
                project.full_clean()
                project.save()
                
                # Create specific status histories to match projects app behavior
                from datetime import time
                
                # 1. Create purchase date status history (if purchase_date_status exists)
                try:
                    purchase_date_status = VideoProjectStatusOption.objects.filter(
                        name__icontains='Purchase Date',
                        is_active=True
                    ).first()
                    
                    if purchase_date_status and project.purchase_date:
                        purchase_datetime = timezone.make_aware(
                            timezone.datetime.combine(project.purchase_date, time(12, 0))
                        )
                        VideoProjectStatusHistory.objects.create(
                            project=project,
                            status=purchase_date_status,
                            changed_by=user,
                            changed_at=purchase_datetime,
                            comments='Video Project Created',
                            category_one_snapshot=purchase_date_status.category_one,
                            category_two_snapshot=purchase_date_status.category_two
                        )
                except Exception as e:
                    logger.warning(f"Could not create purchase date status history: {e}")
                
                # 2. Create sales confirmation status history  
                try:
                    sales_datetime = timezone.make_aware(
                        timezone.datetime.combine(project.sales_confirmation_date, time(12, 0))
                    )
                    VideoProjectStatusHistory.objects.create(
                        project=project,
                        status=project.current_status,
                        changed_by=user,
                        changed_at=sales_datetime,
                        comments=project_data.get('status_change_comment', 'Video Project Created'),
                        category_one_snapshot=project.current_status.category_one,
                        category_two_snapshot=project.current_status.category_two
                    )
                except Exception as e:
                    logger.warning(f"Could not create sales confirmation status history: {e}")
                
                logger.info(f"Created new video project: {project.id} - {project.project_name} by {user.username}")
                return True, project
            
            except ValidationError as e:
                logger.warning(f"Validation error in create_video_project: {str(e)}")
                # Return error messages as a dictionary for field-specific display
                if hasattr(e, 'message_dict'):
                    return False, e.message_dict
                return False, str(e)
            except Exception as e:
                logger.exception(f"Unexpected error in create_video_project: {str(e)}")
                return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def get_video_project(project_id):
        """
        Retrieves a video project by its ID.
        
        Args:
            project_id: UUID of the project
        
        Returns:
            tuple: (success, result)
                - If successful: (True, project_object)
                - If failed: (False, error_message)
        """
        try:
            project = get_object_or_404(
                VideoProject.objects.select_related(
                    'product', 'city', 'video_pm', 'current_status'
                ),
                id=project_id
            )
            return True, project
        except Exception as e:
            logger.warning(f"Video project not found: {project_id} - {str(e)}")
            return False, "Video project not found"
    
    @staticmethod
    def get_video_project_details(project_id):
        """
        Get comprehensive video project details - mirrors projects service.
        """
        success, project = VideoProjectService.get_video_project(project_id)
        if not success:
            return False, project  # project contains error message
        
        return True, {
            'project': project,
            'status_history': project.status_history.select_related(
                'status', 'changed_by'
            ).order_by('-changed_at')[:10],
            'deliveries': project.deliveries.all()
        }
    
    @staticmethod
    @transaction.atomic
    def update_project_status(project_id, status_id, comments, user):
        """
        Update project status and create audit trail - mirrors projects service.
        """
        project = get_object_or_404(VideoProject, id=project_id)
        new_status = get_object_or_404(VideoProjectStatusOption, id=status_id)
        
        if project.current_status == new_status:
            return project  # No change needed
        
        old_status = project.current_status
        project.current_status = new_status
        
        # Set user and comment for the model's save method to use
        project._current_user = user
        project._status_change_comment = comments or ""
        
        # Save project - this will create the status history through the model's save method
        project.save()
        
        return project
    
    @staticmethod
    def get_video_project_list(user, filters=None, project_type='pipeline'):
        """
        Gets a filtered list of video projects for display.
        Works with data from VideoProjectFilterForm.
        Mirrors projects app logic exactly for delivered/pipeline functionality.
        
        Args:
            user: User making the request (must be VIDEO_PM)
            filters: Dictionary of filter parameters  
            project_type: 'pipeline' (default), 'delivered', or 'all'
        
        Returns:
            tuple: (success, queryset)
        """
        try:
            # Base queryset - get all video projects with related data
            queryset = VideoProject.objects.select_related(
                'product',
                'city', 
                'video_pm',
                'current_status'
            ).order_by('-created_at')
            
            # Define the statuses that are considered 'delivered' based on category_two field
            delivered_status_query = Q(category_two__iexact='Final Delivery')
            
            # Apply project type filter
            if project_type == 'pipeline':
                # Get all status IDs that indicate a "delivered" state
                delivered_statuses = VideoProjectStatusOption.objects.filter(
                    delivered_status_query
                ).values_list('id', flat=True)
                
                # Exclude these projects from the pipeline
                if delivered_statuses:
                    queryset = queryset.exclude(current_status_id__in=delivered_statuses)
                    
            elif project_type == 'delivered':
                # Get only projects with a "delivered" status
                delivered_statuses = VideoProjectStatusOption.objects.filter(
                    delivered_status_query
                ).values_list('id', flat=True)
                
                if delivered_statuses:
                    queryset = queryset.filter(current_status_id__in=delivered_statuses)
                else:
                    # No such statuses defined, return empty queryset
                    queryset = queryset.none()
            
            # 'all' type doesn't filter by status - shows everything
            
            if not filters:
                return True, queryset
                
            # Apply filters
            if filters.get('search'):
                search_query = filters['search']
                queryset = queryset.filter(
                    Q(project_name__icontains=search_query) |
                    Q(opportunity_id__icontains=search_query) |
                    Q(builder_name__icontains=search_query)
                )
            
            if filters.get('status'):
                queryset = queryset.filter(current_status=filters['status'])
            
            if filters.get('product'):
                queryset = queryset.filter(product=filters['product'])
            
            if filters.get('region'):
                queryset = queryset.filter(city__region=filters['region'])
            
            if filters.get('city'):
                queryset = queryset.filter(city=filters['city'])
            
            if filters.get('video_pm'):
                queryset = queryset.filter(video_pm=filters['video_pm'])
            
            # Apply date range filters 
            if filters.get('date_from') or filters.get('date_to'):
                if project_type == 'delivered':
                    # For delivered projects, filter by delivery date (status history with Final Delivery)
                    delivery_history_subquery = VideoProjectStatusHistory.objects.filter(
                        project=OuterRef('pk'),
                        status__category_two__iexact='Final Delivery'
                    ).order_by('changed_at').values('changed_at')[:1]
                    
                    queryset = queryset.annotate(
                        delivery_date_annotated=Subquery(delivery_history_subquery)
                    )
                    
                    if filters.get('date_from'):
                        queryset = queryset.filter(delivery_date_annotated__date__gte=filters['date_from'])
                    if filters.get('date_to'):
                        queryset = queryset.filter(delivery_date_annotated__date__lte=filters['date_to'])
                        
                else:
                    # For pipeline projects, filter by latest_status_date
                    if filters.get('date_from'):
                        queryset = queryset.filter(latest_status_date__date__gte=filters['date_from'])
                    if filters.get('date_to'):
                        queryset = queryset.filter(latest_status_date__date__lte=filters['date_to'])
            
            return True, queryset
            
        except Exception as e:
            logger.exception(f"Error in get_video_project_list: {str(e)}")
            return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def get_video_filter_options():
        """Get filter options for project list UI"""
        return {
            'statuses': VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
            'cities': City.objects.all().order_by('name'),
            'products': VideoProduct.objects.filter(is_active=True).order_by('name')
        }
    
    @staticmethod
    def get_pipeline_projects(video_pm):
        """Get active/pipeline video projects (not delivered) - mirrors projects app logic"""
        success, projects = VideoProjectService.get_video_project_list(video_pm, project_type='pipeline')
        if success:
            return projects.filter(video_pm=video_pm)
        return VideoProject.objects.none()
    
    @staticmethod
    def get_delivered_projects(video_pm):
        """Get delivered video projects - mirrors projects app logic"""
        success, projects = VideoProjectService.get_video_project_list(video_pm, project_type='delivered')
        if success:
            return projects.filter(video_pm=video_pm)
        return VideoProject.objects.none()
    
    @staticmethod
    def track_video_project_delivery(project_id):
        """Track delivery performance when project is completed"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            
            # Get current date as delivery date
            delivery_date = timezone.now().date()
            
            # Video projects don't track expected completion dates
            days_variance = None
                
            # Create delivery record
            delivery, created = VideoProjectDelivery.objects.get_or_create(
                project=project,
                delivery_date=delivery_date,
                defaults={
                    'project_name': project.project_name,
                    'hs_id': project.hs_id,
                    'actual_completion_date': delivery_date,
                    'days_variance_snapshot': days_variance
                }
            )
            
            return delivery 