#projects/services.py
import logging
from django.core.exceptions import ValidationError
from .models import Project, DailyRoster, ProjectStatusHistory, ProjectStatusOption, ProductTask, ProjectTask, TaskAssignment, Product, ActiveTimer, TimeSession, DailyTimeTotal, TimerActionLog, ProjectMetrics, ProjectDelivery, TeamMemberMetrics
from django.db.models import Sum, Q, Subquery, OuterRef, F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from accounts.models import User
from locations.models import Region, City
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, timedelta
import calendar
from django.db.models import Avg

logger = logging.getLogger(__name__)

class ProjectService:
    """
    Service class that handles all business logic related to projects.
    This centralizes our project-related operations in one place.
    """
    
    @staticmethod
    def create_project(project_data, user):
        """
        Creates a new project with proper validation and business logic.
        Works with data from any source (forms, API, CLI).
        
        Args:
            project_data: Dictionary with project data
            user: User creating the project (must be DPM)
                    
        Returns:
            tuple: (success, result)
                - If successful: (True, project)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                # Create project object from validated data
                project = Project(
                    opportunity_id=project_data['opportunity_id'],
                    project_name=project_data['project_name'],
                    builder_name=project_data['builder_name'],
                    city=project_data['city'],
                    product=project_data['product'],
                    product_subcategory=project_data.get('product_subcategory'),
                    package_id=project_data.get('package_id'),
                    quantity=project_data['quantity'],
                    purchase_date=project_data['purchase_date'],
                    sales_confirmation_date=project_data['sales_confirmation_date'],
                    account_manager=project_data['account_manager'],
                    current_status=project_data['current_status'],
                    dpm=user,
                    project_type=project_data.get('project_type') or None,
                )
                
                # Set expected TAT from the product if not specified
                if not project_data.get('expected_tat'):
                    project.expected_tat = project.product.expected_tat
                else:
                    project.expected_tat = project_data['expected_tat']
                
                # Generate HS_ID explicitly before saving
                project.hs_id = Project.generate_hs_id()
                
                # Save the new project
                project._current_user = user
                
                if 'status_change_comment' in project_data:
                    project._status_change_comment = project_data['status_change_comment']
                
                # Validate and save
                project.full_clean()
                project.save()
                
                logger.info(f"Created new project: {project.id} - {project.project_name} by {user.username}")
                return True, project
                
            except ValidationError as e:
                logger.warning(f"Validation error in create_project: {str(e)}")
                # Return error messages as a dictionary for field-specific display
                if hasattr(e, 'message_dict'):
                    return False, e.message_dict
                return False, str(e)
            except Exception as e:
                logger.exception(f"Unexpected error in create_project: {str(e)}")
                return False, f"An error occurred: {str(e)}"
   
    @staticmethod
    def get_project(project_id):
        """
        Retrieves a project by its ID.
        
        Args:
            project_id: UUID of the project
                
        Returns:
            tuple: (success, result)
                - If successful: (True, project_object)
                - If failed: (False, error_message)
        """
        try:
            project = Project.objects.get(id=project_id)
            return True, project
        except Project.DoesNotExist:
            logger.info(f"Project with ID {project_id} not found")
            return False, "Project not found"
        except Exception as e:
            logger.exception(f"Error retrieving project {project_id}: {str(e)}")
            return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def get_project_details(project_id):
        """
        Retrieves a project and its related information.
        
        Args:
            project_id: UUID of the project
                
        Returns:
            tuple: (success, result)
                - If successful: (True, (project, status_history))
                - If failed: (False, error_message)
        """
        try:
            project = Project.objects.get(id=project_id)
            
            # Get status history ordered by most recent first
            status_history = project.status_history.all().select_related(
                'status',
                'changed_by'
            ).order_by('-changed_at')
            
            logger.debug(f"Retrieved project details for {project_id}")
            return True, (project, status_history)
        except Project.DoesNotExist:
            logger.info(f"Project with ID {project_id} not found")
            return False, "Project not found"
        except Exception as e:
            logger.exception(f"Error retrieving project details {project_id}: {str(e)}")
            return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def update_project_status(project_id, status_id, user, comments=""):
        """
        Updates a project's status and creates a history record.
        
        Args:
            project_id: UUID of the project
            status_id: UUID of the new status
            user: User making the change
            comments: Optional comments about the status change
                
        Returns:
            tuple: (success, result)
                - If successful: (True, project)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                # Get the project
                project = Project.objects.get(id=project_id)
                
                # Get the new status
                new_status = ProjectStatusOption.objects.get(id=status_id)
                
                # Don't create a history entry if status hasn't changed
                if project.current_status == new_status:
                    return False, "The selected status is already the current status."
                
                # Update the project status
                project.current_status = new_status
                project._current_user = user
                project._status_change_comment = comments
                project.save()
                
                logger.info(f"Updated status for project {project_id} to {new_status.name} by {user.username}")
                return True, project
                
            except Project.DoesNotExist:
                logger.warning(f"Project not found: {project_id}")
                return False, "Project not found."
            except ProjectStatusOption.DoesNotExist:
                logger.warning(f"Status not found: {status_id}")
                return False, "Status not found."
            except ValidationError as e:
                logger.warning(f"Validation error in update_project_status: {str(e)}")
                return False, str(e)
            except Exception as e:
                logger.exception(f"Error updating project status: {str(e)}")
                return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def get_project_list(search_query=None, status=None, product=None, region=None, city=None, dpm=None, page=1, items_per_page=10):
        """
        Retrieves a filtered, searched, and paginated list of projects.
        
        Args:
            search_query: Text to search for in project name, opportunity ID, or builder
            status: Status ID to filter by
            product: Product ID to filter by
            region: Region ID to filter by
            city: City ID to filter by
            dpm: DPM user ID to filter by
            page: Page number for pagination
            items_per_page: Number of items to show per page
                
        Returns:
            tuple: (success, result)
                - If successful: (True, (page_obj, filters_applied))
                - If failed: (False, error_message)
        """
        try:
            # Start with all projects
            queryset = Project.objects.select_related(
                'current_status',
                'product',
                'city',
                'city__region',
                'dpm'
            ).order_by('-created_at')

            # Apply search if provided
            if search_query:
                queryset = queryset.filter(
                    Q(project_name__icontains=search_query) |
                    Q(opportunity_id__icontains=search_query) |
                    Q(builder_name__icontains=search_query)
                )

            # Apply filters
            if status:
                queryset = queryset.filter(current_status_id=status)
            if product:
                queryset = queryset.filter(product_id=product)
            if region:
                queryset = queryset.filter(city__region_id=region)
            if city:
                queryset = queryset.filter(city_id=city)
            if dpm:
                queryset = queryset.filter(dpm_id=dpm)

            # Create paginator
            paginator = Paginator(queryset, items_per_page)
            page_obj = paginator.get_page(page)

            # Track which filters are applied
            filters_applied = {
                'search_query': search_query,
                'status': status,
                'product': product,
                'region': region,
                'city': city,
                'dpm': dpm
            }

            logger.debug(f"Retrieved filtered project list with {paginator.count} total projects")
            return True, (page_obj, filters_applied)
        except Exception as e:
            logger.exception(f"Error retrieving project list: {str(e)}")
            return False, f"An error occurred while retrieving projects: {str(e)}"

    @staticmethod
    def get_filter_options():
        """
        Gets all the options available for filtering projects.
        
        This helps populate filter dropdowns in the UI.
        
        Returns:
            tuple: (success, result)
                - If successful: (True, filter_options_dict)
                - If failed: (False, error_message)
        """
        try:
            filter_options = {
                'statuses': ProjectStatusOption.objects.filter(is_active=True).order_by('order'),
                'products': Product.objects.filter(is_active=True).order_by('name'),
                'cities': City.objects.all().order_by('name'),
                'regions': Region.objects.all().order_by('name'),
                'dpms': User.objects.filter(role='DPM', is_active=True).order_by('username')
            }
            return True, filter_options
        except Exception as e:
            logger.exception(f"Error retrieving filter options: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def create_project_task(project_id, task_data, dpm):
        """
        Creates a new task for a project.
        
        Args:
            project_id: UUID of the project
            task_data: Dictionary with validated form data
            dpm: User object of the DPM
                
        Returns:
            tuple: (success, result)
                - If successful: (True, task)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                project = Project.objects.get(id=project_id)
                
                # Validate the user is the project's DPM
                if project.dpm != dpm:
                    logger.warning(f"User {dpm.id} attempted to create task for project {project_id} but is not the assigned DPM")
                    return False, "Only the assigned DPM can create tasks"
                    
                # Ensure project has been set up
                missing_config = []
                if not project.project_incharge:
                    missing_config.append("Project Incharge")
                if not project.expected_completion_date:
                    missing_config.append("Expected Completion Date")
                    
                if missing_config:
                    logger.warning(f"Attempted to create task for project {project_id} with incomplete configuration: {missing_config}")
                    return False, f"Please complete project configuration first. Missing: {', '.join(missing_config)}"
                
                # Create task object directly from validated data
                task = ProjectTask(
                    project=project,
                    product_task=task_data['product_task'],
                    task_type=task_data['task_type'],
                    estimated_time=task_data['estimated_time'],
                    created_by=dpm
                )
                
                # Save the task (this will generate the task_id)
                task.save()
                
                logger.info(f"Created new task {task.task_id} for project {project_id} by {dpm.username}")
                return True, task
                    
            except Project.DoesNotExist:
                logger.warning(f"Project not found: {project_id}")
                return False, "Project not found"
            except ValidationError as e:
                logger.warning(f"Validation error in create_project_task: {str(e)}")
                return False, e.message_dict if hasattr(e, 'message_dict') else str(e)
            except Exception as e:
                logger.exception(f"Error creating project task: {str(e)}")
                return False, f"An error occurred: {str(e)}"

    @staticmethod
    def create_task_assignment(task_id, assignment_data, dpm):
        """
        Creates a new assignment for a project task.
        
        Args:
            task_id: UUID of the task
            assignment_data: Dictionary with validated form data
            dpm: User object of the DPM
                
        Returns:
            tuple: (success, result)
                - If successful: (True, assignment)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                task = ProjectTask.objects.select_related('project').get(id=task_id)
                
                # Validate the user is the project's DPM
                if task.project.dpm != dpm:
                    logger.warning(f"User {dpm.id} attempted to create assignment for task {task_id} but is not the assigned DPM")
                    return False, "Only the project's DPM can create assignments"
                
                # Create assignment object from validated data
                assignment = TaskAssignment(
                    task=task,
                    assigned_to=assignment_data['assigned_to'],
                    projected_hours=assignment_data['projected_hours'],
                    sub_task=assignment_data['sub_task'],
                    rework_type=assignment_data.get('rework_type'),
                    is_active=True,  # Always set to True for new assignments
                    expected_delivery_date=assignment_data['expected_delivery_date'],
                    assigned_by=dpm
                )

                # Run model validation
                assignment.full_clean()
                
                # Save the assignment (this will generate the assignment_id)
                assignment.save()
                
                logger.info(f"Created task assignment {assignment.assignment_id} for task {task_id} by {dpm.username}")
                return True, assignment
                    
            except ProjectTask.DoesNotExist:
                logger.warning(f"Task not found: {task_id}")
                return False, "Task not found"
            except ValidationError as e:
                logger.warning(f"Validation error in create_task_assignment: {str(e)}")
                return False, e.message_dict if hasattr(e, 'message_dict') else str(e)
            except Exception as e:
                logger.exception(f"Error creating task assignment: {str(e)}")
                return False, f"An error occurred: {str(e)}"


    @staticmethod
    def update_task_assignment(assignment_id, assignment_data, dpm):
        """
        Updates an existing task assignment with performance metrics.
        
        Args:
            assignment_id: UUID of the assignment
            assignment_data: Dictionary with validated form data
            dpm: User object of the DPM
                
        Returns:
            tuple: (success, result)
                - If successful: (True, assignment)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                assignment = TaskAssignment.objects.select_related(
                    'task__project'
                ).get(id=assignment_id)
            
                # Validate DPM permission
                if assignment.task.project.dpm != dpm:
                    logger.warning(f"User {dpm.id} attempted to update assignment {assignment_id} but is not the assigned DPM")
                    return False, "Only the project's DPM can update assignments"
                
                # Update assignment fields from validated data
                if 'projected_hours' in assignment_data:
                    assignment.projected_hours = assignment_data['projected_hours']
                
                if 'expected_delivery_date' in assignment_data:
                    assignment.expected_delivery_date = assignment_data['expected_delivery_date']
                
                if 'error_count' in assignment_data:
                    assignment.error_count = assignment_data['error_count']
                
                if 'error_description' in assignment_data:
                    assignment.error_description = assignment_data['error_description']
                
                if 'quality_rating' in assignment_data:
                    assignment.quality_rating = assignment_data['quality_rating']
                
                if 'is_active' in assignment_data:
                    assignment.is_active = assignment_data['is_active']
                
                # Save the updated assignment
                assignment.save()
                
                logger.info(f"Updated task assignment {assignment.assignment_id} by {dpm.username}")
                return True, assignment
            
            except TaskAssignment.DoesNotExist:
                logger.warning(f"Assignment not found: {assignment_id}")
                return False, "Assignment not found"
            except ValidationError as e:
                logger.warning(f"Validation error in update_task_assignment: {str(e)}")
                return False, str(e)
            except Exception as e:
                logger.exception(f"Error updating task assignment: {str(e)}")
                return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def get_project_task(task_id, project_id=None):
        """
        Retrieves a project task by its ID, optionally validating it belongs to a specific project.
        
        Args:
            task_id: UUID of the task
            project_id: Optional UUID of the project for validation
            
        Returns:
            tuple: (success, result)
                - If successful: (True, task_object)
                - If failed: (False, error_message)
        """
        try:
            query = ProjectTask.objects.select_related('project', 'product_task', 'created_by')
            
            if project_id:
                task = query.get(id=task_id, project_id=project_id)
            else:
                task = query.get(id=task_id)
                
            logger.debug(f"Retrieved project task {task_id}")
            return True, task
            
        except ProjectTask.DoesNotExist:
            logger.info(f"Task with ID {task_id} not found")
            if project_id:
                return False, "Task not found for this project"
            return False, "Task not found"
        except Exception as e:
            logger.exception(f"Error retrieving project task {task_id}: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def get_project_with_tasks(project_id):
        """
        Retrieves a project and its tasks with all related data needed for project management.
        
        Args:
            project_id: UUID of the project
                
        Returns:
            tuple: (success, result)
                - If successful: (True, (project, tasks))
                - If failed: (False, error_message)
        """
        try:
            project = Project.objects.get(id=project_id)
            
            tasks = ProjectTask.objects.filter(
                project=project
            ).prefetch_related(
                'assignments',
                'assignments__assigned_to'
            ).select_related(
                'product_task',
                'created_by'
            ).order_by('-created_at')
            
            logger.debug(f"Retrieved project {project_id} with {tasks.count()} tasks")
            return True, (project, tasks)
        
        except Project.DoesNotExist:
            logger.warning(f"Project not found: {project_id}")
            return False, "Project not found"
        except Exception as e:
            logger.exception(f"Error retrieving project with tasks: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def get_task_assignment(assignment_id):
        """
        Retrieves a task assignment by its ID with all related information.
        
        Args:
            assignment_id: UUID of the assignment
            
        Returns:
            tuple: (success, result)
                - If successful: (True, assignment_object)
                - If failed: (False, error_message)
        """
        try:
            assignment = TaskAssignment.objects.select_related(
                'task__project',
                'task__product_task',
                'assigned_to',
                'assigned_by'
            ).get(id=assignment_id)
            
            logger.debug(f"Retrieved task assignment {assignment_id}")
            return True, assignment
            
        except TaskAssignment.DoesNotExist:
            logger.info(f"Assignment with ID {assignment_id} not found")
            return False, "Assignment not found"
        except Exception as e:
            logger.exception(f"Error retrieving assignment {assignment_id}: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def get_task_with_assignments(task_id):
        """
        Retrieves a task with all its assignments.
        
        Args:
            task_id: UUID of the task
            
        Returns:
            tuple: (success, result)
                - If successful: (True, (task, assignments))
                - If failed: (False, error_message)
        """
        try:
            task = ProjectTask.objects.select_related(
                'project',
                'product_task',
                'created_by'
            ).get(id=task_id)
            
            assignments = task.assignments.select_related(
                'assigned_to',
                'assigned_by'
            ).order_by('-assigned_date')
            
            logger.debug(f"Retrieved task {task_id} with {assignments.count()} assignments")
            return True, (task, assignments)
        except ProjectTask.DoesNotExist:
            logger.warning(f"Task not found: {task_id}")
            return False, "Task not found"
        except Exception as e:
            logger.exception(f"Error retrieving task with assignments: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def update_project_configuration(project_id, config_data, dpm):
        """
        Updates a project's configuration (incharge, completion date, rating).
        Also updates any existing delivery records if rating changes.
        """
        with transaction.atomic():
            try:
                project = Project.objects.get(id=project_id)
                
                # Validate the user is the project's DPM
                if project.dpm != dpm:
                    logger.warning(f"User {dpm.id} attempted to update configuration for project {project_id} but is not the assigned DPM")
                    return False, "Only the assigned DPM can update project configuration"
                
                # Store old values for comparison
                old_rating = project.delivery_performance_rating
                old_incharge = project.project_incharge
                
                # Update project with validated data
                project.project_incharge = config_data['project_incharge']
                project.expected_completion_date = config_data['expected_completion_date']
                
                # Only update rating if provided
                if config_data.get('delivery_performance_rating') is not None:
                    project.delivery_performance_rating = config_data['delivery_performance_rating']
                
                project.save()
                
                # If delivery rating changed, update any existing ProjectDelivery records
                if old_rating != project.delivery_performance_rating:
                    from .models import ProjectDelivery
                    updated_count = ProjectDelivery.objects.filter(project=project).update(
                        delivery_performance_rating=project.delivery_performance_rating
                    )
                    
                    if updated_count > 0:
                        logger.info(f"Updated {updated_count} delivery records for project {project_id} with new rating {project.delivery_performance_rating}")
                        
                        # Recalculate metrics for all affected dates
                        deliveries = ProjectDelivery.objects.filter(project=project)
                        for delivery in deliveries:
                            ReportingService.calculate_team_member_metrics(
                                delivery.project_incharge,
                                delivery.delivery_date
                            )
                
                # If project incharge changed, update delivery records
                if old_incharge != project.project_incharge and project.project_incharge:
                    ProjectDelivery.objects.filter(project=project).update(
                        project_incharge=project.project_incharge
                    )
                
                logger.info(f"Updated project configuration for {project_id} by {dpm.username}")
                return True, project
                    
            except Project.DoesNotExist:
                logger.warning(f"Project not found: {project_id}")
                return False, "Project not found"
            except ValidationError as e:
                logger.warning(f"Validation error in update_project_configuration: {str(e)}")
                return False, str(e)
            except Exception as e:
                logger.exception(f"Error updating project configuration: {str(e)}")
                return False, f"An error occurred: {str(e)}"

    @staticmethod
    def get_dpm_projects_for_task_management(dpm):
        """
        Retrieves all projects for a DPM formatted for task management view.
        
        Args:
            dpm: The DPM user
                
        Returns:
            tuple: (success, result)
                - If successful: (True, projects_queryset)
                - If failed: (False, error_message)
        """
        try:
            # Get the latest status history for each project
            latest_status = ProjectStatusHistory.objects.filter(
                project=OuterRef('pk')
            ).order_by('-changed_at')

            # Get all projects for this DPM with latest status info
            projects = Project.objects.filter(
                dpm=dpm
            ).annotate(
                latest_status_name=Subquery(
                    latest_status.values('status__name')[:1]
                ),
                latest_status_date=Subquery(
                    latest_status.values('changed_at')[:1]
                )
            ).select_related(
                'product',
                'project_incharge'
            ).order_by('-created_at')
            
            logger.debug(f"Retrieved {projects.count()} projects for DPM {dpm.id}")
            return True, projects
        
        except Exception as e:
            logger.exception(f"Error retrieving DPM projects: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def get_team_member_assignments(team_member):
        """
        Retrieves active assignments for a team member.
        
        Args:
            team_member: The team member user
                
        Returns:
            tuple: (success, result)
                - If successful: (True, assignments_queryset)
                - If failed: (False, error_message)
        """
        try:
            # Get active assignments for this team member
            assignments = TaskAssignment.objects.filter(
                assigned_to=team_member,
                is_active=True
            ).select_related(
                'task__project',
                'task__product_task'
            ).order_by('expected_delivery_date')
            
            logger.debug(f"Retrieved {assignments.count()} active assignments for team member {team_member.id}")
            return True, assignments
        
        except Exception as e:
            logger.exception(f"Error retrieving team member assignments: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def validate_hs_id_sequence():
        """
        Validates the HS_ID sequence and identifies any gaps or duplicates.
        Returns a list of issues found, if any.
        """
        issues = []
        try:
            with transaction.atomic():
                projects = Project.objects.select_for_update().order_by('created_at')
                expected_sequence = {}
                
                for project in projects:
                    if not project.hs_id:
                        issues.append(f"Project {project.id} has no HS_ID")
                        continue
                        
                    letter = project.hs_id[0]
                    number = int(project.hs_id[1:])
                    
                    if letter not in expected_sequence:
                        expected_sequence[letter] = 1
                    
                    if number != expected_sequence[letter]:
                        issues.append(
                            f"Gap detected: Expected {letter}{expected_sequence[letter]}, "
                            f"found {project.hs_id} for project {project.project_name}"
                        )
                    
                    expected_sequence[letter] = number + 1
                    
                    # Check for numbers exceeding 999
                    if number > 999:
                        issues.append(
                            f"Invalid number range: {project.hs_id} exceeds maximum "
                            f"allowed number (999) for project {project.project_name}"
                        )
                
                return issues
                
        except Exception as e:
            return [f"Error validating HS_ID sequence: {str(e)}"]

    @staticmethod
    def repair_hs_id_sequence():
        """
        Attempts to repair any issues in the HS_ID sequence.
        Returns a tuple of (success, result) where result is either the number of
        fixed issues or an error message.
        """
        try:
            with transaction.atomic():
                projects = Project.objects.select_for_update().order_by('created_at')
                current_letter = 'A'
                current_number = 1
                fixed_count = 0
                
                for project in projects:
                    new_hs_id = f'{current_letter}{current_number}'
                    
                    # Only update if the HS_ID is different
                    if project.hs_id != new_hs_id:
                        project.hs_id = new_hs_id
                        project.save()
                        fixed_count += 1
                    
                    # Increment sequence
                    current_number += 1
                    if current_number > 999:
                        current_letter = chr(ord(current_letter) + 1)
                        current_number = 1
                
                return True, f"Fixed {fixed_count} HS_ID issues"
                
        except Exception as e:
            return False, f"Error repairing HS_ID sequence: {str(e)}"
        
    


    @staticmethod
    def start_timer(assignment_id, team_member):
        """
        Start a timer for a team member on a specific assignment.
        FIXED: Added select_for_update to prevent race conditions.
        """
        with transaction.atomic():
            try:
                # FIXED: Use select_for_update to prevent race conditions
                existing_timer = ActiveTimer.objects.select_for_update().filter(
                    team_member=team_member
                ).first()
                
                if existing_timer:
                    return False, f"Cannot start timer! Task {existing_timer.assignment.assignment_id} is currently running. Please stop it first."
                
                # FIXED: Lock the assignment to prevent concurrent modifications
                assignment = TaskAssignment.objects.select_for_update().get(id=assignment_id)
                
                # Check if assignment is completed
                if assignment.is_completed:
                    return False, f"Cannot start timer! Task {assignment.assignment_id} is marked as completed."
                
                # Verify team member is assigned to this task
                if assignment.assigned_to != team_member:
                    return False, "You can only start timers for assignments assigned to you."
                
                # Create active timer
                active_timer = ActiveTimer.objects.create(
                    assignment=assignment,
                    team_member=team_member,
                    started_at=timezone.now()
                )
                
                # Log the action
                TimerActionLog.objects.create(
                    assignment=assignment,
                    team_member=team_member,
                    action='START',
                    details=f"Started timer at {active_timer.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                logger.info(f"Timer started for {team_member.username} on {assignment.assignment_id}")
                return True, active_timer
                
            except TaskAssignment.DoesNotExist:
                logger.warning(f"Assignment not found: {assignment_id}")
                return False, "Assignment not found"
            except Exception as e:
                logger.exception(f"Error starting timer: {str(e)}")
                return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def stop_timer(team_member, description=""):
        """
        Stop the active timer for a team member.
        FIXED: Added select_for_update and minimum duration validation.
        """
        with transaction.atomic():
            try:
                # FIXED: Use select_for_update to prevent race conditions
                active_timer = ActiveTimer.objects.select_for_update().filter(
                    team_member=team_member
                ).first()
                
                if not active_timer:
                    return False, "No active timer found to stop."
                
                end_time = timezone.now()
                start_time = active_timer.started_at
                
                # Calculate duration in minutes
                duration_seconds = (end_time - start_time).total_seconds()
                # FIXED: Ensure minimum 1 minute duration
                duration_minutes = max(1, int(duration_seconds // 60))
                
                # Determine the work date (use start time's date)
                work_date = start_time.date()
                
                # Create time session
                time_session = TimeSession.objects.create(
                    assignment=active_timer.assignment,
                    team_member=team_member,
                    started_at=start_time,
                    ended_at=end_time,
                    duration_minutes=duration_minutes,
                    date_worked=work_date,
                    description=description,
                    session_type='TIMER'
                )
                
                # FIXED: Use atomic daily total update
                ProjectService._update_daily_total(
                    active_timer.assignment, 
                    team_member, 
                    work_date, 
                    duration_minutes
                )
                
                # Log the action
                TimerActionLog.objects.create(
                    assignment=active_timer.assignment,
                    team_member=team_member,
                    action='STOP',
                    details=f"Stopped timer at {end_time.strftime('%Y-%m-%d %H:%M:%S')}, Duration: {ProjectService._format_minutes(duration_minutes)}"
                )
                
                # Delete the active timer
                active_timer.delete()
                
                logger.info(f"Timer stopped for {team_member.username}, Duration: {duration_minutes} minutes")
                return True, time_session
                
            except Exception as e:
                logger.exception(f"Error stopping timer: {str(e)}")
                return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def add_manual_time(assignment_id, team_member, date_worked, hours, minutes, description=""):
        """
        Add manual time entry for an assignment.
        
        Args:
            assignment_id: UUID of the assignment
            team_member: User object of the team member
            date_worked: Date object for when work was done
            hours: Integer hours worked
            minutes: Integer minutes worked
            description: Optional description of work done
            
        Returns:
            tuple: (success, result)
                - If successful: (True, time_session_object)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                # Get the assignment
                assignment = TaskAssignment.objects.get(id=assignment_id)
                
                # Verify team member is assigned to this task
                if assignment.assigned_to != team_member:
                    return False, "You can only add time for assignments assigned to you."
                
                # Calculate total minutes
                total_minutes = (hours * 60) + minutes
                if total_minutes <= 0:
                    return False, "Duration must be greater than 0 minutes."
                
                # Create time session
                time_session = TimeSession.objects.create(
                    assignment=assignment,
                    team_member=team_member,
                    started_at=timezone.make_aware(datetime.combine(date_worked, datetime.min.time())),
                    ended_at=timezone.make_aware(datetime.combine(date_worked, datetime.min.time()) + timedelta(minutes=total_minutes)),
                    duration_minutes=total_minutes,
                    date_worked=date_worked,
                    description=description,
                    session_type='MANUAL'
                )
                
                # Update daily total
                ProjectService._update_daily_total(assignment, team_member, date_worked, total_minutes)
                
                # Log the action
                TimerActionLog.objects.create(
                    assignment=assignment,
                    team_member=team_member,
                    action='MANUAL_ADD',
                    details=f"Added {ProjectService._format_minutes(total_minutes)} for {date_worked}, Description: {description}"
                )
                
                logger.info(f"Manual time added for {team_member.username} on {assignment.assignment_id}: {total_minutes} minutes")
                return True, time_session
                
            except TaskAssignment.DoesNotExist:
                logger.warning(f"Assignment not found: {assignment_id}")
                return False, "Assignment not found"
            except Exception as e:
                logger.exception(f"Error adding manual time: {str(e)}")
                return False, f"An error occurred: {str(e)}"
    
    @staticmethod
    def complete_assignment(assignment_id, team_member):
        """
        Mark an assignment as completed.
        UPDATED: Added validation to prevent completion of assignments with zero hours worked.
        
        Args:
            assignment_id: UUID of the assignment
            team_member: User object of the team member
            
        Returns:
            tuple: (success, result)
                - If successful: (True, assignment_object)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                assignment = TaskAssignment.objects.select_for_update().get(id=assignment_id)
                
                # Verify team member is assigned to this task
                if assignment.assigned_to != team_member:
                    return False, "You can only complete assignments assigned to you."
                
                # Check if already completed
                if assignment.is_completed:
                    return False, "This assignment is already marked as completed."
                
                # NEW: Check if any time has been logged for this assignment
                total_worked_minutes = DailyTimeTotal.objects.filter(
                    assignment=assignment,
                    team_member=team_member
                ).aggregate(total=Sum('total_minutes'))['total'] or 0
                
                if total_worked_minutes == 0:
                    return False, "Cannot complete assignment with zero hours worked. Please log some time before marking this assignment as completed."
                
                # Stop any active timer for this assignment
                active_timer = ActiveTimer.objects.filter(
                    team_member=team_member,
                    assignment=assignment
                ).first()
                
                if active_timer:
                    # Stop the timer first
                    success, result = ProjectService.stop_timer(team_member, "Completed assignment")
                    if not success:
                        return False, f"Error stopping timer: {result}"
                
                # Mark as completed
                assignment.is_completed = True
                assignment.completion_date = timezone.now()
                assignment.is_active = False  # Remove from active assignments
                assignment.save()
                
                # Log the action
                TimerActionLog.objects.create(
                    assignment=assignment,
                    team_member=team_member,
                    action='COMPLETE',
                    details=f"Assignment completed at {assignment.completion_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                logger.info(f"Assignment {assignment.assignment_id} completed by {team_member.username}")
                return True, assignment
                
            except TaskAssignment.DoesNotExist:
                logger.warning(f"Assignment not found: {assignment_id}")
                return False, "Assignment not found"
            except Exception as e:
                logger.exception(f"Error completing assignment: {str(e)}")
                return False, f"An error occurred: {str(e)}"

    
    @staticmethod
    def edit_session_duration(session_id, team_member, new_duration_minutes):
        """
        Edit the duration of a timer session (not manual entries).
        Recalculates the daily total after editing.
        """
        with transaction.atomic():
            try:
                # Get the session with validation
                session = TimeSession.objects.select_related('assignment').get(
                    id=session_id,
                    team_member=team_member,
                    session_type='TIMER'  # Only allow editing timer sessions
                )
                
                # Validate new duration
                if new_duration_minutes <= 0:
                    return False, "Duration must be greater than 0 minutes"
                
                if new_duration_minutes > 1440:  # 24 hours
                    return False, "Duration cannot exceed 24 hours"
                
                # Store old duration for recalculation
                old_duration = session.duration_minutes
                
                # Update session duration and mark as edited
                session.duration_minutes = new_duration_minutes
                session.is_edited = True  # NEW: Mark as edited
                session.save()
                
                # Recalculate daily total
                ProjectService._recalculate_daily_total(
                    session.assignment, 
                    team_member, 
                    session.date_worked
                )
                
                # Log the action
                TimerActionLog.objects.create(
                    assignment=session.assignment,
                    team_member=team_member,
                    action='EDIT_SESSION',
                    details=f"Edited session duration from {ProjectService._format_minutes(old_duration)} to {ProjectService._format_minutes(new_duration_minutes)}"
                )
                
                logger.info(f"Session duration edited for {team_member.username}: {session_id}")
                return True, session
                
            except TimeSession.DoesNotExist:
                logger.warning(f"Timer session not found or not editable: {session_id}")
                return False, "Timer session not found or you don't have permission to edit it"
            except Exception as e:
                logger.exception(f"Error editing session duration: {str(e)}")
                return False, f"An error occurred: {str(e)}"

    @staticmethod
    def _recalculate_daily_total(assignment, team_member, work_date):
        """
        Recalculate daily total from all sessions for a specific date.
        This replaces manual editing and ensures consistency.
        """
        with transaction.atomic():
            try:
                # Calculate total from all sessions for this date
                total_minutes = TimeSession.objects.filter(
                    assignment=assignment,
                    team_member=team_member,
                    date_worked=work_date
                ).aggregate(
                    total=Sum('duration_minutes')
                )['total'] or 0
                
                # Update or create daily total
                daily_total, created = DailyTimeTotal.objects.get_or_create(
                    assignment=assignment,
                    team_member=team_member,
                    date_worked=work_date,
                    defaults={'total_minutes': total_minutes}
                )
                
                if not created:
                    daily_total.total_minutes = total_minutes
                    # Mark as not manually edited since we're recalculating from sessions
                    daily_total.is_manually_edited = False
                    daily_total.save()
                    
            except Exception as e:
                logger.exception(f"Error recalculating daily total: {str(e)}")
        
    @staticmethod
    def get_team_member_dashboard_data(team_member):
        """
        Get all data needed for team member dashboard.
        Verified to include product information.
        """
        try:
            today = date.today()
            
            # Get active assignments - VERIFY select_related includes product path
            active_assignments = TaskAssignment.objects.filter(
                assigned_to=team_member,
                is_active=True,
                is_completed=False
            ).select_related(
                'task__project',           # For project info
                'task__project__product',  # ADD: For product name
                'task__product_task'       # For task name
            ).order_by('expected_delivery_date')
            
            # Get completed assignments (last 7 days) - VERIFY select_related includes product path
            week_ago = today - timedelta(days=7)
            completed_assignments = TaskAssignment.objects.filter(
                assigned_to=team_member,
                is_completed=True,
                completion_date__gte=week_ago
            ).select_related(
                'task__project',           # For project info
                'task__project__product',  # ADD: For product name  
                'task__product_task'       # For task name
            ).order_by('-completion_date')
            
            # Get active timer
            active_timer = ActiveTimer.objects.filter(team_member=team_member).select_related('assignment').first()
            
            # Calculate today's total hours
            today_total_minutes = DailyTimeTotal.objects.filter(
                team_member=team_member,
                date_worked=today
            ).aggregate(total=Sum('total_minutes'))['total'] or 0
            
            # Add total working hours to each assignment
            for assignment in active_assignments:
                assignment.total_working_hours = ProjectService._get_assignment_total_hours(assignment)
            
            for assignment in completed_assignments:
                assignment.total_working_hours = ProjectService._get_assignment_total_hours(assignment)
            
            # Calculate elapsed time for active timer
            elapsed_time = None
            if active_timer:
                elapsed_seconds = (timezone.now() - active_timer.started_at).total_seconds()
                elapsed_minutes = int(elapsed_seconds // 60)
                elapsed_time = {
                    'hours': elapsed_minutes // 60,
                    'minutes': elapsed_minutes % 60,
                    'seconds': int(elapsed_seconds % 60),
                    'formatted': ProjectService._format_minutes(elapsed_minutes)
                }
            
            dashboard_data = {
                'active_assignments': active_assignments,
                'completed_assignments': completed_assignments,
                'active_timer': active_timer,
                'elapsed_time': elapsed_time,
                'today_summary': {
                    'total_minutes': today_total_minutes,
                    'formatted_total': ProjectService._format_minutes(today_total_minutes)
                }
            }
            
            return True, dashboard_data
            
        except Exception as e:
            logger.exception(f"Error getting dashboard data: {str(e)}")
            return False, f"An error occurred: {str(e)}"
    
    # Helper methods (private)
    @staticmethod
    def _update_daily_total(assignment, team_member, work_date, additional_minutes):
        """Update or create daily total by adding minutes. SAFE from race conditions."""
        with transaction.atomic():
            try:
                # First, try to get or create the daily total
                daily_total, created = DailyTimeTotal.objects.get_or_create(
                    assignment=assignment,
                    team_member=team_member,
                    date_worked=work_date,
                    defaults={'total_minutes': additional_minutes}
                )
                
                if not created and not daily_total.is_manually_edited:
                    # Use F() expression for atomic update - prevents race conditions
                    DailyTimeTotal.objects.filter(
                        id=daily_total.id,
                        is_manually_edited=False  # Double-check it wasn't manually edited
                    ).update(
                        total_minutes=F('total_minutes') + additional_minutes,
                        last_updated=timezone.now()
                    )
                    
            except Exception as e:
                logger.exception(f"Error updating daily total atomically: {str(e)}")
                # Fallback to non-atomic update if F() fails (rare edge case)
                try:
                    daily_total.refresh_from_db()
                    if not daily_total.is_manually_edited:
                        daily_total.total_minutes += additional_minutes
                        daily_total.save()
                except Exception as fallback_error:
                    logger.exception(f"Fallback update also failed: {fallback_error}")
    
    @staticmethod
    def _format_minutes(total_minutes):
        """Convert minutes to HH:MM format."""
        if total_minutes is None:
            return "00:00"
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"
    
    @staticmethod
    def _get_assignment_total_hours(assignment):
        """Get total hours for an assignment across all days."""
        total_minutes = DailyTimeTotal.objects.filter(
            assignment=assignment
        ).aggregate(total=Sum('total_minutes'))['total'] or 0
        
        return ProjectService._format_minutes(total_minutes)
    @staticmethod
    def get_assignment_for_timesheet(assignment_id, team_member):
        """
        Get assignment for timesheet view with permission check.
        Updated to include all related data needed for display.
        
        Args:
            assignment_id: UUID of the assignment
            team_member: User object of the team member
            
        Returns:
            tuple: (success, result)
                - If successful: (True, assignment_object)
                - If failed: (False, error_message)
        """
        try:
            # Add select_related to fetch all needed related data in one query
            assignment = TaskAssignment.objects.select_related(
                'task',                    # For task details and task_type
                'task__project',           # For project name and details
                'task__project__product',  # For product name
                'task__product_task',      # For product task name
                'assigned_by'              # For who assigned it (optional, good to have)
            ).get(id=assignment_id, assigned_to=team_member)
            
            return True, assignment
        except TaskAssignment.DoesNotExist:
            return False, "Assignment not found or not assigned to you"
        except Exception as e:
            logger.exception(f"Error getting assignment for timesheet: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    # Updated method in services.py - ProjectService class

    @staticmethod
    def get_assignment_timesheet_data(assignment_id, team_member):
        """
        Get all timesheet data for an assignment.
        UPDATED: Now shows quality_rating instead of error_count for completed assignments.
        """
        try:
            # First verify assignment access
            success, assignment = ProjectService.get_assignment_for_timesheet(assignment_id, team_member)
            if not success:
                return False, assignment
            
            # Get ALL daily totals (no date filtering)
            daily_totals = DailyTimeTotal.objects.filter(
                assignment=assignment,
                team_member=team_member
            ).order_by('-date_worked')
            
            # Get ALL individual sessions (no date filtering)
            sessions = TimeSession.objects.filter(
                assignment=assignment,
                team_member=team_member
            ).order_by('-started_at')
            
            # Add editability flag and helper properties to each session
            for session in sessions:
                # Only allow editing timer sessions AND only if assignment is not completed
                session.is_editable = (session.session_type == 'TIMER' and not assignment.is_completed)
                
                # Add helper properties for template use (to avoid template filter issues)
                duration = session.duration_minutes or 0
                session.duration_hours = duration // 60
                session.duration_minutes_part = duration % 60
            
            # Calculate assignment summary metrics
            total_worked_minutes = sum(dt.total_minutes for dt in daily_totals)
            projected_minutes = assignment.projected_hours or 0
            
            # Calculate progress percentage
            if projected_minutes > 0:
                progress_percentage = min(100, (total_worked_minutes / projected_minutes) * 100)
            else:
                progress_percentage = 0
            
            # Calculate days worked
            days_worked = daily_totals.count()
            
            # Calculate timer usage percentage (for both active and completed)
            timer_usage_percentage = ProjectService._calculate_timer_usage_percentage(assignment, team_member)
            
            # UPDATED: Create assignment summary based on completion status
            if assignment.is_completed:
                # For completed assignments: Days Worked | Task Productivity | Quality Rating | Timer Usage %
                if total_worked_minutes > 0 and projected_minutes > 0:
                    task_productivity = (projected_minutes / total_worked_minutes) * 100
                    productivity_display = f"{task_productivity:.1f}%"
                elif projected_minutes == 0:
                    productivity_display = "N/A"
                else:
                    productivity_display = "0%"
                
                # UPDATED: Show quality_rating instead of error_count with color coding
                if assignment.quality_rating:
                    quality_rating_display = f"{assignment.quality_rating:.1f}"
                    # Add color class based on rating
                    if assignment.quality_rating >= 4.0:
                        quality_rating_class = "text-success"
                    elif assignment.quality_rating >= 3.0:
                        quality_rating_class = "text-warning"
                    else:
                        quality_rating_class = "text-danger"
                else:
                    quality_rating_display = "Not Rated"
                    quality_rating_class = "text-muted"
                
                assignment_summary = {
                    'total_worked_formatted': ProjectService._format_minutes(total_worked_minutes),
                    'projected_formatted': ProjectService._format_minutes(projected_minutes),
                    'progress_percentage': round(progress_percentage, 1),
                    'days_worked': days_worked,
                    'task_productivity': productivity_display,
                    'quality_rating': quality_rating_display,  # CHANGED: from error_count
                    'quality_rating_class': quality_rating_class,  # NEW: CSS class for coloring
                    'timer_usage_percentage': f"{timer_usage_percentage:.1f}%",
                    'total_sessions': sessions.count(),
                    'is_completed': True
                }
            else:
                # For active assignments: Days Worked | Days Remaining | Timer Usage %
                days_remaining = ProjectService._calculate_days_remaining(assignment.expected_delivery_date)
                
                assignment_summary = {
                    'total_worked_formatted': ProjectService._format_minutes(total_worked_minutes),
                    'projected_formatted': ProjectService._format_minutes(projected_minutes),
                    'progress_percentage': round(progress_percentage, 1),
                    'days_worked': days_worked,
                    'days_remaining': days_remaining,
                    'timer_usage_percentage': f"{timer_usage_percentage:.1f}%",
                    'total_sessions': sessions.count(),
                    'is_completed': False
                }
            
            timesheet_data = {
                'assignment': assignment,
                'daily_totals': daily_totals,
                'sessions': sessions,
                'assignment_summary': assignment_summary
            }
            
            return True, timesheet_data
            
        except Exception as e:
            logger.exception(f"Error getting timesheet data: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def get_daily_roster_data(team_member, selected_date, show_week=False):
        """
        Get daily roster data for team member.
        
        Args:
            team_member: User object of the team member
            selected_date: Date to show roster for
            show_week: Boolean to show entire week
            
        Returns:
            tuple: (success, result)
                - If successful: (True, roster_data_dict)
                - If failed: (False, error_message)
        """
        try:
            if show_week:
                # Show entire week
                start_date = selected_date - timedelta(days=selected_date.weekday())
                end_date = start_date + timedelta(days=6)
                date_range = f"Week of {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
            else:
                # Show single day
                start_date = end_date = selected_date
                date_range = selected_date.strftime('%B %d, %Y')
            
            # Get daily totals
            daily_totals = DailyTimeTotal.objects.filter(
                team_member=team_member,
                date_worked__gte=start_date,
                date_worked__lte=end_date
            ).select_related('assignment__task__project').order_by('date_worked', 'assignment__assignment_id')
            
            # Calculate total
            total_minutes = sum(dt.total_minutes for dt in daily_totals)
            total_formatted = ProjectService._format_minutes(total_minutes)
            
            roster_data = {
                'daily_totals': daily_totals,
                'date_range': date_range,
                'total_formatted': total_formatted,
                'show_week': show_week
            }
            
            return True, roster_data
            
        except Exception as e:
            logger.exception(f"Error getting roster data: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        

    @staticmethod
    def get_or_create_daily_roster(team_member, date):
        """
        Get or create a daily roster entry with smart defaults.
        
        Args:
            team_member: User object
            date: Date object
            
        Returns:
            tuple: (daily_roster_object, created_boolean)
        """
        with transaction.atomic():
            try:
                # Determine default status based on day of week and holidays
                day_of_week = date.weekday()  # Monday=0, Sunday=6
                
                # Check if it's a holiday first
                from .models import Holiday
                is_holiday = Holiday.objects.filter(
                    date=date,
                    location='Gurgaon',  # You can make this configurable later
                    is_active=True
                ).exists()
                
                if is_holiday:
                    default_status = 'HOLIDAY'
                elif day_of_week in [5, 6]:  # Saturday=5, Sunday=6
                    default_status = 'WEEK_OFF'
                else:
                    default_status = 'PRESENT'
                
                # Calculate assignment hours from existing DailyTimeTotal
                assignment_minutes = DailyTimeTotal.objects.filter(
                    team_member=team_member,
                    date_worked=date
                ).aggregate(total=Sum('total_minutes'))['total'] or 0
                
                daily_roster, created = DailyRoster.objects.get_or_create(
                    team_member=team_member,
                    date=date,
                    defaults={
                        'status': default_status,
                        'assignment_hours': assignment_minutes,
                        'is_auto_created': True
                    }
                )
                
                # If existing record, sync assignment hours
                if not created and daily_roster.assignment_hours != assignment_minutes:
                    daily_roster.assignment_hours = assignment_minutes
                    daily_roster.save()
                
                return daily_roster, created
                
            except Exception as e:
                logger.exception(f"Error creating daily roster: {str(e)}")
                return None, False
    @staticmethod
    def get_monthly_roster(team_member, year, month):
        """
        Get monthly roster data for a team member with proper calendar structure.
        Updated to include detailed hour breakdowns.
        """
        try:
            # Get all dates in the month
            _, last_day = calendar.monthrange(year, month)
            month_dates = [
                date(year, month, day) 
                for day in range(1, last_day + 1)
            ]
            
            # Get or create roster entries for all dates
            roster_dict = {}
            for single_date in month_dates:
                roster, created = ProjectService.get_or_create_daily_roster(team_member, single_date)
                if roster:
                    # Add computed properties for template
                    roster.task_hours_formatted = ProjectService._format_minutes(roster.assignment_hours)
                    roster.misc_hours_formatted = ProjectService._format_minutes(roster.misc_hours)
                    roster.total_hours_formatted = ProjectService._format_minutes(roster.total_hours)
                    roster_dict[single_date.day] = roster
            
            # Create calendar grid structure with Sunday as first day
            cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
            calendar_weeks = []
            
            for week in cal.monthdays2calendar(year, month):
                week_data = []
                for day, weekday in week:
                    if day == 0:
                        # Empty cell for days from other months
                        week_data.append(None)
                    else:
                        # Get roster data for this day
                        roster_data = roster_dict.get(day)
                        week_data.append(roster_data)
                calendar_weeks.append(week_data)
            
            # Calculate monthly summary from actual roster entries
            roster_entries = list(roster_dict.values())
            total_present_days = len([r for r in roster_entries if r.status == 'PRESENT'])
            total_leave_days = len([r for r in roster_entries if r.status in ['LEAVE', 'SICK_LEAVE']])
            total_weekoffs = len([r for r in roster_entries if r.status == 'WEEK_OFF'])
            total_assignment_hours = sum(r.assignment_hours for r in roster_entries)
            total_misc_hours = sum(r.misc_hours for r in roster_entries)
            
            monthly_data = {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'calendar_weeks': calendar_weeks,
                'roster_entries': roster_entries,
                'month_dates': month_dates,
                'summary': {
                    'total_days': len(month_dates),
                    'present_days': total_present_days,
                    'leave_days': total_leave_days,
                    'weekoff_days': total_weekoffs,
                    'task_hours': ProjectService._format_minutes(total_assignment_hours),
                    'misc_hours': ProjectService._format_minutes(total_misc_hours),
                    'total_hours': ProjectService._format_minutes(total_assignment_hours + total_misc_hours)
                }
            }
            
            return True, monthly_data
            
        except Exception as e:
            logger.exception(f"Error getting monthly roster: {str(e)}")
            return False, f"An error occurred: {str(e)}"
        
    @staticmethod
    def update_roster_status(team_member, date, new_status, misc_hours=0, misc_description="", notes=""):
        """
        Update roster status and misc hours for a specific date.
        
        Args:
            team_member: User object
            date: Date object
            new_status: String status value
            misc_hours: Integer minutes for misc work
            misc_description: String description of misc work
            notes: String additional notes
            
        Returns:
            tuple: (success, result)
                - If successful: (True, roster_object)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                roster, created = ProjectService.get_or_create_daily_roster(team_member, date)
                
                if not roster:
                    return False, "Could not create roster entry"
                
                # Update fields
                roster.status = new_status
                roster.misc_hours = misc_hours
                roster.misc_description = misc_description
                roster.notes = notes
                roster.is_auto_created = False  # Mark as manually edited
                roster.save()
                
                logger.info(f"Updated roster for {team_member.username} on {date}: {new_status}")
                return True, roster
                
            except Exception as e:
                logger.exception(f"Error updating roster status: {str(e)}")
                return False, f"An error occurred: {str(e)}"
        

    @staticmethod
    def add_misc_hours(team_member, work_date, activity, duration_hours, duration_minutes):
        """
        Add miscellaneous hours to a team member's daily roster.
        These are HR activities (meetings, training, admin) not related to task work.
        UPDATED: Now safe from race conditions using atomic updates.
        
        Args:
            team_member: User object
            work_date: Date object
            activity: String description of the activity
            duration_hours: Integer hours
            duration_minutes: Integer minutes
            
        Returns:
            tuple: (success, result)
                - If successful: (True, roster_object)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                # Calculate total minutes
                total_minutes = (duration_hours * 60) + duration_minutes
                
                if total_minutes <= 0:
                    return False, "Duration must be at least 1 minute"
                
                if total_minutes > 1440:  # 24 hours
                    return False, "Duration cannot exceed 24 hours"
                
                # Get or create daily roster
                roster, created = ProjectService.get_or_create_daily_roster(team_member, work_date)
                
                if not roster:
                    return False, "Could not create roster entry"
                
                # Format the activity description
                formatted_duration = ProjectService._format_minutes(total_minutes)
                new_activity = f"{activity} ({formatted_duration})"
                
                # SAFE: Use atomic updates with F() expressions to prevent race conditions
                from django.db.models import F, Case, When, Value
                from django.db.models.functions import Concat
                
                # Atomic update of misc_hours and description
                updated_rows = DailyRoster.objects.filter(id=roster.id).update(
                    misc_hours=F('misc_hours') + total_minutes,
                    misc_description=Case(
                        # If description is empty or null, use new activity
                        When(misc_description='', then=Value(new_activity)),
                        When(misc_description__isnull=True, then=Value(new_activity)),
                        # Otherwise, append to existing description
                        default=Concat('misc_description', Value(f'; {new_activity}'))
                    ),
                    is_auto_created=False  # Mark as manually edited
                )
                
                if updated_rows == 0:
                    return False, "Failed to update roster - it may have been deleted"
                
                # Refresh the roster object to get updated values for return
                roster.refresh_from_db()
                
                logger.info(f"Misc hours added for {team_member.username} on {work_date}: {total_minutes} minutes")
                return True, roster
                
            except Exception as e:
                logger.exception(f"Error adding misc hours: {str(e)}")
                return False, f"An error occurred: {str(e)}"


    @staticmethod
    def _calculate_timer_usage_percentage(assignment, team_member):
        """
        Calculate what percentage of total work time came from timer sessions vs manual entries.
        
        For edited timer sessions, we split the contribution:
        - Timer contribution: min(original_duration, final_duration) 
        - Manual contribution: max(0, final_duration - original_duration)
        
        This logic respects user intent when editing:
        - Editing down (75→60 mins): User says only 60 mins was actual timer work
        - Editing up (60→75 mins): Timer captured 60 mins, user added 15 mins manually
        
        Args:
            assignment: TaskAssignment object
            team_member: User object
            
        Returns:
            float: Timer usage percentage (0.0 to 100.0)
        """
        try:
            # Get all time sessions for this assignment
            sessions = TimeSession.objects.filter(
                assignment=assignment,
                team_member=team_member
            )
            
            if not sessions.exists():
                return 0.0
            
            timer_minutes = 0
            manual_minutes = 0
            
            for session in sessions:
                session_duration = session.duration_minutes or 0
                
                if session.session_type == 'MANUAL':
                    # Manual entries: 100% manual contribution
                    manual_minutes += session_duration
                    
                elif session.session_type == 'TIMER':
                    if not session.is_edited:
                        # Unedited timer sessions: 100% timer contribution
                        timer_minutes += session_duration
                    else:
                        # Edited timer sessions: Split contribution based on original vs final duration
                        if session.started_at and session.ended_at:
                            # Calculate original timer duration (what the timer actually recorded)
                            original_duration_seconds = (session.ended_at - session.started_at).total_seconds()
                            original_duration_minutes = int(original_duration_seconds // 60)
                            
                            # Final duration is what the user edited it to
                            final_duration_minutes = session_duration
                            
                            if final_duration_minutes <= original_duration_minutes:
                                # User edited down: timer contributed the final amount, no manual addition
                                timer_minutes += final_duration_minutes
                                # manual_minutes += 0  (no manual contribution)
                            else:
                                # User edited up: timer contributed original amount, user added the difference manually
                                timer_minutes += original_duration_minutes
                                manual_minutes += (final_duration_minutes - original_duration_minutes)
                        else:
                            # Fallback: if timestamps are missing, treat as 100% timer
                            # (This shouldn't happen based on user confirmation, but defensive programming)
                            timer_minutes += session_duration
            
            total_minutes = timer_minutes + manual_minutes
            
            if total_minutes == 0:
                return 0.0
            
            # Calculate percentage with proper rounding
            timer_percentage = (timer_minutes / total_minutes) * 100
            return round(timer_percentage, 1)
            
        except Exception as e:
            logger.exception(f"Error calculating timer usage percentage: {str(e)}")
            return 0.0

    @staticmethod
    def _calculate_days_remaining(expected_delivery_date):
        """
        Calculate and format days remaining until expected delivery date.
        
        Args:
            expected_delivery_date: datetime object
            
        Returns:
            str: Formatted string like "3 days", "Due Today", or "Overdue by 2 days"
        """
        try:
            if not expected_delivery_date:
                return "No deadline set"
            
            # Convert to date if it's a datetime object
            if hasattr(expected_delivery_date, 'date'):
                expected_date = expected_delivery_date.date()
            else:
                expected_date = expected_delivery_date
            
            today = date.today()
            days_difference = (expected_date - today).days
            
            if days_difference > 0:
                return f"{days_difference} days"
            elif days_difference == 0:
                return "Due Today"
            else:
                return f"Overdue by {abs(days_difference)} days"
                
        except Exception as e:
            logger.exception(f"Error calculating days remaining: {str(e)}")
            return "Unknown"

class ReportingService:
    """
    Service layer for all reporting functionality.
    Handles metric calculations, aggregations, and caching.
    """
    @staticmethod
    def calculate_team_member_metrics(team_member, date):
        """
        Calculate and store daily metrics for a team member.
        """
        with transaction.atomic():
            from decimal import Decimal, InvalidOperation
            import math
            
            # Get or create metrics record
            metrics, created = TeamMemberMetrics.objects.get_or_create(
                team_member=team_member,
                date=date
            )
            
            # 1. Calculate Productivity & Quality (completed assignments)
            completed_assignments = TaskAssignment.objects.filter(
                assigned_to=team_member,
                is_completed=True,
                completion_date__date=date
            )
            
            total_projected = 0
            total_worked = 0
            quality_sum = Decimal('0')
            quality_count = 0
            
            for assignment in completed_assignments:
                total_projected += assignment.projected_hours or 0
                
                # Get actual worked hours
                worked_minutes = DailyTimeTotal.objects.filter(
                    assignment=assignment,
                    team_member=team_member
                ).aggregate(total=Sum('total_minutes'))['total'] or 0
                
                total_worked += worked_minutes
                
                # Quality metrics
                if assignment.quality_rating:
                    quality_sum += Decimal(str(assignment.quality_rating))
                    quality_count += 1
            
            # 2. Calculate Utilization
            daily_roster = DailyRoster.objects.filter(
                team_member=team_member,
                date=date
            ).first()
            
            if daily_roster and daily_roster.status == 'PRESENT':
                available_minutes = 480  # 8 hours
                worked_today = DailyTimeTotal.objects.filter(
                    team_member=team_member,
                    date_worked=date
                ).aggregate(total=Sum('total_minutes'))['total'] or 0
                
                # Add misc hours
                worked_today += daily_roster.misc_hours
                
                metrics.available_minutes = available_minutes
                # Safely calculate utilization
                if available_minutes > 0:
                    utilization = Decimal(str(worked_today)) / Decimal(str(available_minutes)) * 100
                    # Cap at 999.99 (max for 5,2 decimal field)
                    metrics.utilization_score = min(utilization, Decimal('999.99'))
                else:
                    metrics.utilization_score = Decimal('0')
            else:
                metrics.utilization_score = None
            
            # 3. Calculate Delivery Performance
            delivered_projects = ProjectDelivery.objects.filter(
                project_incharge=team_member,
                delivery_date=date
            )
            
            delivery_sum = Decimal('0')
            delivery_count = 0
            
            for delivery in delivered_projects:
                if delivery.delivery_performance_rating is not None and delivery.delivery_performance_rating > 0:
                    delivery_sum += Decimal(str(delivery.delivery_performance_rating))
                    delivery_count += 1
            
            # Update all metrics with safe calculations
            metrics.total_projected_minutes = total_projected
            metrics.total_worked_minutes = total_worked
            
            # Safely calculate productivity
            if total_worked > 0:
                productivity = Decimal(str(total_projected)) / Decimal(str(total_worked)) * 100
                # Cap at 999.99 (max for 5,2 decimal field)
                metrics.productivity_score = min(productivity, Decimal('999.99'))
            else:
                metrics.productivity_score = None
            
            metrics.assignments_completed = completed_assignments.count()
            metrics.total_quality_points = quality_sum
            
            # Safely calculate average quality
            if quality_count > 0:
                avg_quality = quality_sum / Decimal(str(quality_count))
                # Ensure it's within 1-5 range
                metrics.average_quality_rating = min(max(avg_quality, Decimal('1')), Decimal('5'))
            else:
                metrics.average_quality_rating = None
            
            metrics.projects_delivered = delivered_projects.count()  # Total projects delivered
            metrics.total_delivery_rating_points = delivery_sum
            
            # Safely calculate average delivery rating
            if delivery_count > 0:
                avg_delivery = delivery_sum / Decimal(str(delivery_count))
                # Ensure it's within 1-5 range
                metrics.average_delivery_rating = min(max(avg_delivery, Decimal('1')), Decimal('5'))
            else:
                metrics.average_delivery_rating = None
            
            try:
                metrics.save()
            except InvalidOperation as e:
                logger.error(f"Invalid decimal operation for {team_member.username} on {date}: {str(e)}")
                # Log the values for debugging
                logger.error(f"Values - Productivity: {metrics.productivity_score}, Utilization: {metrics.utilization_score}")
                raise
            
            return metrics
    
    @staticmethod
    def track_project_delivery(project, delivery_date=None):
        """
        Track when a project reaches final delivery status.
        This should be called when project status changes to "Final Delivery".
        """
        with transaction.atomic():
            if not delivery_date:
                delivery_date = date.today()
            
            # Check if already tracked
            existing = ProjectDelivery.objects.filter(
                project=project,
                delivery_date=delivery_date
            ).first()
        
        if existing:
            # Update the rating if it changed
            if project.delivery_performance_rating and existing.delivery_performance_rating != project.delivery_performance_rating:
                existing.delivery_performance_rating = project.delivery_performance_rating
                existing.save()
                logger.info(f"Updated delivery rating for project {project.hs_id} to {project.delivery_performance_rating}")
            return existing
        
        # Create delivery record
        if not project.project_incharge:
            logger.warning(f"Project {project.hs_id} reached final delivery without project incharge")
            return None
        
        # Only create delivery record if there's a valid rating
        delivery = ProjectDelivery.objects.create(
            project=project,
            project_incharge=project.project_incharge,
            delivery_date=delivery_date,
            delivery_performance_rating=project.delivery_performance_rating or None,  # Store None instead of 0
            project_name=project.project_name,
            hs_id=project.hs_id,
            expected_completion_date=project.expected_completion_date,
            actual_completion_date=delivery_date
        )
        
        # Recalculate metrics for the project incharge on this date
        ReportingService.calculate_team_member_metrics(
            project.project_incharge,
            delivery_date
        )
        
        logger.info(f"Tracked delivery for project {project.hs_id} with rating {delivery.delivery_performance_rating}")
        return delivery
    
    @staticmethod
    def get_team_member_report(team_member, start_date, end_date):
        """
        Get comprehensive report including delivery performance.
        """
        # Get daily metrics
        daily_metrics = TeamMemberMetrics.objects.filter(
            team_member=team_member,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Calculate aggregates
        aggregates = daily_metrics.aggregate(
            avg_productivity=Avg('productivity_score'),
            avg_utilization=Avg('utilization_score'),
            avg_quality=Avg('average_quality_rating'),
            avg_delivery=Avg('average_delivery_rating'),
            total_assignments=Sum('assignments_completed'),
            total_projects_delivered=Sum('projects_delivered'),
            total_projected=Sum('total_projected_minutes'),
            total_worked=Sum('total_worked_minutes')
        )
        
        # Get detailed delivery history
        delivery_history = ProjectDelivery.objects.filter(
            project_incharge=team_member,
            delivery_date__range=[start_date, end_date]
        ).order_by('-delivery_date')
        
        # Calculate on-time delivery rate
        on_time_count = delivery_history.filter(days_variance__lte=0).count()
        total_deliveries = delivery_history.count()
        on_time_rate = (on_time_count / total_deliveries * 100) if total_deliveries > 0 else None
        
        return {
            'period': f"{start_date} to {end_date}",
            'daily_metrics': daily_metrics,
            'delivery_history': delivery_history,
            'summary': {
                'average_productivity': aggregates['avg_productivity'],
                'average_utilization': aggregates['avg_utilization'],
                'average_quality_rating': aggregates['avg_quality'],
                'average_delivery_rating': aggregates['avg_delivery'],
                'total_assignments_completed': aggregates['total_assignments'],
                'total_projects_delivered': aggregates['total_projects_delivered'],
                'on_time_delivery_rate': on_time_rate,
                'total_hours_projected': (aggregates['total_projected'] or 0) / 60,
                'total_hours_worked': (aggregates['total_worked'] or 0) / 60,
            },
            'charts_data': ReportingService._prepare_chart_data(daily_metrics)
        }

    @staticmethod
    def calculate_project_metrics(project, date):
        """
        Calculate and store daily metrics for a project.
        Handles delivery performance rating when status changes to Final Delivery.
        """
        with transaction.atomic():
            metrics, created = ProjectMetrics.objects.get_or_create(
                project=project,
                date=date
            )
        
        # Update basic info
        metrics.project_incharge = project.project_incharge
        metrics.delivery_performance_rating = project.delivery_performance_rating
        metrics.status_name = project.current_status.name
        
        # Check if this is Final Delivery
        if 'final' in project.current_status.name.lower() and 'delivery' in project.current_status.name.lower():
            metrics.is_final_delivery = True
        
        # Calculate completion
        total_tasks = project.tasks.count()
        completed_tasks = project.tasks.filter(
            assignments__is_completed=True
        ).distinct().count()
        
        metrics.tasks_total = total_tasks
        metrics.tasks_completed = completed_tasks
        metrics.completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        metrics.save()
        return metrics
    
    @staticmethod
    def get_organization_dashboard(start_date, end_date):
        """
        Get organization-wide dashboard metrics.
        """
        # This would aggregate across all team members and projects
        # Implementation details...
        pass
    
    @staticmethod
    def _prepare_chart_data(daily_metrics):
        """
        Prepare data for chart visualization.
        """

        import json
    
        data = {
            'dates': [m.date.strftime('%Y-%m-%d') for m in daily_metrics],
            'productivity': [float(m.productivity_score) if m.productivity_score else 0 for m in daily_metrics],
            'utilization': [float(m.utilization_score) if m.utilization_score else 0 for m in daily_metrics],
            'quality': [float(m.average_quality_rating) if m.average_quality_rating else 0 for m in daily_metrics],
        }
        
        return json.dumps(data)