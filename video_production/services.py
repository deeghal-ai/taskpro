from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import VideoProject, VideoProjectStatusOption, VideoProjectStatusHistory, VideoCut, VoiceoverScript, VideoProjectDelivery, VideoProduct
from locations.models import City
from datetime import datetime

class VideoProjectService:
    @staticmethod
    def create_video_project(project_data, user):
        """Create new video production project with validation"""
        with transaction.atomic():
            # Generate unique HS_ID with VP_ prefix for Video Production
            year_month = datetime.now().strftime('%Y%m')
            last_project = VideoProject.objects.filter(
                hs_id__startswith=f'VP_{year_month}_'
            ).order_by('-hs_id').first()
            
            if last_project:
                # Extract the sequence number and increment
                last_number = int(last_project.hs_id.split('_')[2])
                new_number = last_number + 1
            else:
                new_number = 1
                
            hs_id = f'VP_{year_month}_{new_number:04d}'
            
            # Get the default status (first status in order)
            initial_status = VideoProjectStatusOption.objects.filter(
                is_active=True
            ).order_by('order').first()
            
            if not initial_status:
                raise ValueError("No active video project status options found. Please create status options first.")
            
            # Create the video project
            video_project = VideoProject.objects.create(
                hs_id=hs_id,
                opportunity_id=project_data['opportunity_id'],
                project_name=project_data['project_name'],
                builder_name=project_data['builder_name'],
                city=project_data['city'],
                video_product=project_data['video_product'],
                quantity=project_data.get('quantity', 1),
                production_vendor=project_data['production_vendor'],
                shoot_location=project_data.get('shoot_location', ''),
                shoot_date=project_data.get('shoot_date'),
                video_duration_minutes=project_data.get('video_duration_minutes'),
                purchase_date=project_data['purchase_date'],
                expected_completion_date=project_data['expected_completion_date'],
                voiceover_required=project_data.get('voiceover_required', True),
                max_cuts_allowed=project_data.get('max_cuts_allowed', 7),
                video_pm=user,
                current_status=initial_status
            )
            
            # Create initial status history
            VideoProjectStatusHistory.objects.create(
                project=video_project,
                status=initial_status,
                changed_by=user,
                comments=f"Project created by {user.get_full_name() or user.username}"
            )
            
            return video_project
    
    @staticmethod
    def get_video_project(project_id):
        """Get single video project"""
        return get_object_or_404(VideoProject, id=project_id)
    
    @staticmethod
    def get_video_project_details(project_id):
        """Get project with full details including cuts and voiceover history"""
        project = get_object_or_404(
            VideoProject.objects.select_related(
                'video_product', 'city', 'video_pm', 'current_status'
            ).prefetch_related(
                'cuts',
                'voiceover_scripts',
                'status_history__status',
                'status_history__changed_by'
            ),
            id=project_id
        )
        
        return {
            'project': project,
            'cuts': project.cuts.all(),
            'voiceover_scripts': project.voiceover_scripts.all(),
            'status_history': project.status_history.all()[:10],  # Last 10 status changes
            'delivery': getattr(project, 'delivery', None)
        }
    
    @staticmethod
    def update_video_project_status(project_id, status_id, comments, user):
        """Update project status and create history record"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            new_status = get_object_or_404(VideoProjectStatusOption, id=status_id)
            
            # Update project status
            old_status = project.current_status
            project.current_status = new_status
            project.save()
            
            # Create status history record
            VideoProjectStatusHistory.objects.create(
                project=project,
                status=new_status,
                changed_by=user,
                comments=comments or f"Status changed from {old_status.name} to {new_status.name}"
            )
            
            return project
    
    @staticmethod
    def submit_video_cut(project_id, cut_number, user):
        """Submit a video cut for client review"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            
            # Update project's current cut number
            if cut_number > project.current_cut_number:
                project.current_cut_number = cut_number
                project.save()
            
            # Create or update the cut record
            cut, created = VideoCut.objects.get_or_create(
                project=project,
                cut_number=cut_number,
                defaults={
                    'status': 'DELIVERED'
                }
            )
            
            if not created:
                cut.status = 'DELIVERED'
                cut.delivered_date = timezone.now()
                cut.save()
            
            return cut
    
    @staticmethod
    def request_cut_rework(project_id, cut_number, feedback, user):
        """Request rework on a video cut"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            cut = get_object_or_404(VideoCut, project=project, cut_number=cut_number)
            
            cut.status = 'REWORK_REQUESTED'
            cut.rework_required = True
            cut.client_feedback = feedback
            cut.feedback_received_date = timezone.now()
            cut.save()
            
            return cut
    
    @staticmethod
    def submit_voiceover_script(project_id, script_content, user):
        """Submit voiceover script for approval"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            
            # Get the next script version number
            last_script = VoiceoverScript.objects.filter(project=project).order_by('-script_version').first()
            next_version = (last_script.script_version + 1) if last_script else 1
            
            # Create new voiceover script
            script = VoiceoverScript.objects.create(
                project=project,
                script_version=next_version,
                script_content=script_content,
                status='SHARED'
            )
            
            # Update project voiceover status
            project.voiceover_status = 'SCRIPT_SHARED'
            project.save()
            
            return script
    
    @staticmethod
    def approve_voiceover_script(project_id, script_version, user):
        """Approve voiceover script"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            script = get_object_or_404(VoiceoverScript, project=project, script_version=script_version)
            
            script.status = 'APPROVED'
            script.approved_date = timezone.now()
            script.save()
            
            # Update project voiceover status
            project.voiceover_status = 'SCRIPT_APPROVED'
            project.save()
            
            return script
    
    @staticmethod
    def get_video_project_list(video_pm, filters=None):
        """Get filtered list of projects for video PM"""
        queryset = VideoProject.objects.select_related(
            'video_product', 'city', 'current_status'
        ).filter(video_pm=video_pm)
        
        if filters:
            if filters.get('status'):
                queryset = queryset.filter(current_status=filters['status'])
            
            if filters.get('vendor'):
                queryset = queryset.filter(
                    production_vendor__icontains=filters['vendor']
                )
            
            if filters.get('city'):
                queryset = queryset.filter(city=filters['city'])
            
            if filters.get('video_product'):
                queryset = queryset.filter(video_product=filters['video_product'])
            
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(project_name__icontains=search_term) |
                    Q(builder_name__icontains=search_term) |
                    Q(hs_id__icontains=search_term) |
                    Q(opportunity_id__icontains=search_term)
                )
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_video_filter_options():
        """Get filter options for project list UI"""
        return {
            'statuses': VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
            'cities': City.objects.all().order_by('name'),
            'video_products': VideoProduct.objects.filter(is_active=True).order_by('name'),
            'vendors': VideoProject.objects.values_list('production_vendor', flat=True).distinct()
        }
    
    @staticmethod
    def get_pipeline_projects(video_pm):
        """Get active/pipeline video projects (not completed)"""
        completed_statuses = VideoProjectStatusOption.objects.filter(
            category='COMPLETED',
            is_active=True
        )
        
        return VideoProject.objects.select_related(
            'video_product', 'city', 'current_status'
        ).filter(video_pm=video_pm).exclude(
            current_status__in=completed_statuses
        ).order_by('-created_at')
    
    @staticmethod
    def get_delivered_projects(video_pm):
        """Get delivered/completed video projects"""
        completed_statuses = VideoProjectStatusOption.objects.filter(
            category='COMPLETED',
            is_active=True
        )
        
        return VideoProject.objects.select_related(
            'video_product', 'city', 'current_status'
        ).filter(
            video_pm=video_pm,
            current_status__in=completed_statuses
        ).order_by('-actual_delivery_date', '-created_at')
    
    @staticmethod
    def track_video_project_delivery(project_id):
        """Track delivery performance when project is completed"""
        with transaction.atomic():
            project = get_object_or_404(VideoProject, id=project_id)
            
            if not project.actual_delivery_date:
                project.actual_delivery_date = timezone.now().date()
                project.save()
            
            # Calculate delivery performance
            expected_date = project.expected_completion_date
            actual_date = project.actual_delivery_date
            days_variance = (actual_date - expected_date).days
            
            if days_variance > 0:
                rating = 'DELAYED'
            elif days_variance < 0:
                rating = 'EARLY'
            else:
                rating = 'ON_TIME'
            
            # Count total cuts and voiceover iterations
            total_cuts = project.cuts.count()
            voiceover_iterations = project.voiceover_scripts.count()
            
            # Create or update delivery record
            delivery, created = VideoProjectDelivery.objects.get_or_create(
                project=project,
                defaults={
                    'delivery_performance_rating': rating,
                    'delivery_date': actual_date,
                    'days_variance': days_variance,
                    'total_cuts_delivered': total_cuts,
                    'voiceover_iterations': voiceover_iterations
                }
            )
            
            if not created:
                delivery.delivery_performance_rating = rating
                delivery.delivery_date = actual_date
                delivery.days_variance = days_variance
                delivery.total_cuts_delivered = total_cuts
                delivery.voiceover_iterations = voiceover_iterations
                delivery.save()
            
            return delivery 