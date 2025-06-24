#projects/services.py
import logging
from django.core.exceptions import ValidationError
from .models import Project, DailyRoster, ProjectStatusHistory, ProjectStatusOption, ProductTask, ProjectTask, TaskAssignment, Product, ActiveTimer, TimeSession, DailyTimeTotal, TimerActionLog, ProjectDelivery
from django.db.models import Sum, Q, Subquery, OuterRef, F, Prefetch
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
    def update_project_status(project_id, status_id, user, comments="", status_date=None):
        """
        Updates a project's status and creates a history record.

        Args:
            project_id: UUID of the project
            status_id: UUID of the new status
            user: User making the change
            comments: Optional comments about the status change
            status_date: Optional date when the status change occurred (defaults to now)

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
                # Pass the custom status date to the project save method
                if status_date:
                    project._status_change_date = status_date
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
    def get_project_list(search_query=None, status=None, product=None, region=None, city=None, dpm=None, page=1, items_per_page=10, project_type='pipeline'):
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
            project_type: 'pipeline' (default), 'delivered', or 'all'

        Returns:
            tuple: (success, result)
                - If successful: (True, (page_obj, filters_applied))
                - If failed: (False, error_message)
        """
        try:
            # Create a subquery to get the latest status change date for each project
            latest_status_date_subquery = ProjectStatusHistory.objects.filter(
                project=OuterRef('pk')
            ).order_by('-changed_at').values('changed_at')[:1]

            # Start with all projects, annotating them with the latest status date
            queryset = Project.objects.annotate(
                latest_status_date=Subquery(latest_status_date_subquery)
            ).select_related(
                'current_status',
                'product',
                'city',
                'city__region',
                'dpm'
            ).order_by(F('latest_status_date').desc(nulls_last=True), '-created_at')

            # Define the statuses that are considered 'delivered' or 'terminated'
            delivered_status_query = (
                (Q(name__icontains='final') & Q(name__icontains='delivery')) |
                Q(name__iexact='Deemed Consumed') |
                Q(name__iexact='Opp Dropped')
            )

            # Apply project type filter
            if project_type == 'pipeline':
                # Get all status IDs that indicate a "delivered" or "terminated" state
                delivered_statuses = ProjectStatusOption.objects.filter(
                    delivered_status_query
                ).values_list('id', flat=True)

                # Exclude these projects from the pipeline
                if delivered_statuses:
                    queryset = queryset.exclude(current_status_id__in=delivered_statuses)

            elif project_type == 'delivered':
                # Get only projects with a "delivered" or "terminated" status
                delivered_statuses = ProjectStatusOption.objects.filter(
                    delivered_status_query
                ).values_list('id', flat=True)

                if delivered_statuses:
                    queryset = queryset.filter(current_status_id__in=delivered_statuses)
                else:
                    # No such statuses defined, return empty queryset
                    queryset = queryset.none()

            # Store all applied filters to pass back to the template
            filters_applied = {
                'search': search_query,
                'status': status,
                'product': product,
                'region': region,
                'city': city,
                'dpm': dpm,
            }

            # Apply search filter
            if search_query:
                queryset = queryset.filter(
                    Q(hs_id__icontains=search_query) |
                    Q(project_name__icontains=search_query) |
                    Q(opportunity_id__icontains=search_query) |
                    Q(builder_name__icontains=search_query)
                )

            # Apply other filters
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

            # Paginate the results
            paginator = Paginator(queryset, items_per_page)
            page_obj = paginator.get_page(page)

            logger.debug(f"Retrieved filtered project list ({project_type}) with {paginator.count} total projects")
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

                # Import ProjectDelivery for potential use
                from .models import ProjectDelivery

                # If delivery rating changed, update any existing ProjectDelivery records
                if old_rating != project.delivery_performance_rating:
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
    def get_dpm_projects_for_task_management(dpm, pipeline_only=True):
        """
        Retrieves all projects for a DPM with their tasks and assignments,
        optimized for the DPM task management dashboard.

        Args:
            dpm: The DPM user object.
            pipeline_only: If True, excludes projects with a 'delivered' status.

        Returns:
            tuple: (success, result)
        """
        try:
            # Start with projects assigned to the DPM
            projects_qs = Project.objects.filter(dpm=dpm)

            # Exclude projects with certain statuses
            excluded_statuses = [
                "Final Delivery",
                "Opp Dropped",
                "Deemed Consumed"
            ]
            if pipeline_only:
                projects_qs = projects_qs.exclude(current_status__name__in=excluded_statuses)

            # Prefetch related data for performance
            projects_with_tasks = projects_qs.select_related(
                'current_status', 'product'
            ).prefetch_related(
                Prefetch(
                    'tasks',
                    queryset=ProjectTask.objects.select_related('product_task').prefetch_related(
                        Prefetch(
                            'assignments',
                            queryset=TaskAssignment.objects.select_related(
                                'assigned_to'
                            ).order_by('-assigned_date')
                        )
                    )
                )
            ).order_by('-created_at')

            logger.debug(f"Retrieved {projects_with_tasks.count()} projects for DPM {dpm.id}")
            return True, projects_with_tasks

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

                # Calculate duration in seconds
                duration_seconds = (end_time - start_time).total_seconds()

                # NEW: Prevent stopping if less than 1 minute has been recorded
                if duration_seconds < 60:
                    logger.warning(f"Attempt to stop timer for {team_member.username} with less than 1 minute recorded. Duration: {duration_seconds} seconds")
                    return False, "Timer must be run for at least 1 minute before stopping."

                # Calculate duration in minutes, ensuring minimum 1 minute for recording
                duration_minutes = int(duration_seconds // 60)
                if duration_minutes < 1:
                    duration_minutes = 1 # Ensure at least 1 minute is recorded if it's been over 60 seconds but less than 2 minutes.

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

            # Get today's roster data for misc hours and total hours
            today_roster, _ = ProjectService.get_or_create_daily_roster(team_member, today)
            
            dashboard_data = {
                'active_assignments': active_assignments,
                'completed_assignments': completed_assignments,
                'active_timer': active_timer,
                'elapsed_time': elapsed_time,
                'today_summary': {
                    'assignment_minutes': today_total_minutes,
                    'misc_minutes': today_roster.misc_hours,
                    'total_minutes': today_roster.total_hours,
                    'formatted_assignment': ProjectService._format_minutes(today_total_minutes),
                    'formatted_misc': ProjectService._format_minutes(today_roster.misc_hours),
                    'formatted_total': ProjectService._format_minutes(today_roster.total_hours)
                }
            }

            return True, dashboard_data

        except Exception as e:
            logger.exception(f"Error getting dashboard data: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def get_team_member_all_completed_assignments(team_member, start_date=None, end_date=None):
        """
        Get completed assignments for a team member with optional date range filtering.
        Returns assignments ordered by completion date (most recent first).

        Args:
            team_member: User object
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)
        """
        try:
            # Build base query
            query = TaskAssignment.objects.filter(
                assigned_to=team_member,
                is_completed=True
            )

            # Apply date range filtering if provided
            if start_date:
                query = query.filter(completion_date__gte=start_date)
            if end_date:
                query = query.filter(completion_date__lte=end_date)

            # Get completed assignments with related data
            completed_assignments = query.select_related(
                'task__project',           # For project info
                'task__project__product',  # For product name
                'task__product_task'       # For task name
            ).order_by('-completion_date')  # Most recent first

            # Add total working hours to each assignment
            for assignment in completed_assignments:
                assignment.total_working_hours = ProjectService._get_assignment_total_hours(assignment)

            # Calculate average quality rating for context
            rated_assignments = [a for a in completed_assignments if a.quality_rating]
            if rated_assignments:
                avg_quality = sum(a.quality_rating for a in rated_assignments) / len(rated_assignments)
                # Add average quality as an attribute for template use
                completed_assignments.avg_quality_rating = round(avg_quality, 1)
                completed_assignments.rated_count = len(rated_assignments)
            else:
                completed_assignments.avg_quality_rating = None
                completed_assignments.rated_count = 0

            # Calculate average productivity (projected/worked * 100)
            productivity_values = []
            for assignment in completed_assignments:
                # Get projected minutes
                projected_minutes = assignment.projected_hours or 0

                # Get worked minutes from daily totals
                from django.db.models import Sum
                worked_minutes = DailyTimeTotal.objects.filter(
                    assignment=assignment
                ).aggregate(total=Sum('total_minutes'))['total'] or 0

                if worked_minutes > 0 and projected_minutes > 0:
                    productivity = (projected_minutes / worked_minutes) * 100
                    # Cap at reasonable maximum (999%)
                    productivity_values.append(min(productivity, 999))

            if productivity_values:
                completed_assignments.avg_productivity = round(sum(productivity_values) / len(productivity_values), 1)
                completed_assignments.productive_assignments_count = len(productivity_values)
            else:
                completed_assignments.avg_productivity = None
                completed_assignments.productive_assignments_count = 0

            return True, completed_assignments

        except Exception as e:
            logger.exception(f"Error getting all completed assignments: {str(e)}")
            return False, f"An error occurred: {str(e)}"

    @staticmethod
    def get_dpm_all_task_assignments(assignment_status='all', team_member=None, project=None, dpm=None, start_date=None, end_date=None):
        """
        Get all task assignments with filtering options (accessible to any DPM).
        
        Args:
            assignment_status: 'all', 'active', or 'completed'
            team_member: Optional User object to filter by team member
            project: Optional Project object to filter by project
            dpm: Optional DPM User object to filter by DPM
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            tuple: (success, result)
                - If successful: (True, assignments_queryset)
                - If failed: (False, error_message)
        """
        try:
            # Base query - get all assignments (no DPM restriction)
            query = TaskAssignment.objects.select_related(
                'task',
                'task__project', 
                'task__product_task',
                'assigned_to',
                'assigned_by'
            ).prefetch_related(
                'daily_totals'
            )
            
            # Filter by assignment status
            if assignment_status == 'active':
                query = query.filter(is_completed=False)
            elif assignment_status == 'completed':
                query = query.filter(is_completed=True)
            # 'all' doesn't need additional filtering
            
            # Filter by team member
            if team_member:
                query = query.filter(assigned_to=team_member)
            
            # Filter by project
            if project:
                query = query.filter(task__project=project)
            
            # Filter by DPM
            if dpm:
                query = query.filter(task__project__dpm=dpm)
            
            # Apply date filtering based on assignment status
            if start_date or end_date:
                if assignment_status == 'completed':
                    # For completed assignments, filter by completion_date
                    if start_date:
                        query = query.filter(completion_date__date__gte=start_date)
                    if end_date:
                        query = query.filter(completion_date__date__lte=end_date)
                else:
                    # For active assignments (or all), filter by assigned_date
                    if start_date:
                        query = query.filter(assigned_date__date__gte=start_date)
                    if end_date:
                        query = query.filter(assigned_date__date__lte=end_date)
            
            # Order by appropriate date field
            if assignment_status == 'completed':
                query = query.order_by('-completion_date')
            else:
                query = query.order_by('-assigned_date')
            
            # Add computed fields for display
            assignments = []
            for assignment in query:
                # Calculate total hours worked
                total_minutes = sum(dt.total_minutes for dt in assignment.daily_totals.all())
                total_hours_formatted = ProjectService._format_minutes(total_minutes)
                
                # Calculate progress percentage
                if assignment.projected_hours and assignment.projected_hours > 0:
                    progress_percentage = min(100, (total_minutes / assignment.projected_hours) * 100)
                else:
                    progress_percentage = 0
                
                # Add computed fields to assignment object
                assignment.total_hours_worked = total_hours_formatted
                assignment.progress_percentage = round(progress_percentage, 1)
                assignment.projected_hours_formatted = ProjectService._format_minutes(assignment.projected_hours or 0)
                
                assignments.append(assignment)
            
            return True, assignments
            
        except Exception as e:
            logger.exception(f"Error getting DPM task assignments: {str(e)}")
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
                # For completed assignments: Days Worked | Task Productivity | Quality Rating | Optimization | Timer Usage %
                if total_worked_minutes > 0 and projected_minutes > 0:
                    task_productivity = (projected_minutes / total_worked_minutes) * 100
                    productivity_display = f"{task_productivity:.1f}%"
                elif projected_minutes == 0:
                    productivity_display = "N/A"
                else:
                    productivity_display = "0%"

                # Calculate optimization: (projected - worked) / projected * 100
                if projected_minutes > 0:
                    optimization_percentage = ((projected_minutes - total_worked_minutes) / projected_minutes) * 100
                    optimization_display = f"{optimization_percentage:.1f}%"
                    # Add color class based on optimization value
                    if optimization_percentage >= 20:
                        optimization_class = "text-success"
                    elif optimization_percentage >= 10:
                        optimization_class = "text-info"
                    elif optimization_percentage >= 0:
                        optimization_class = "text-warning"
                    else:
                        optimization_class = "text-danger"
                else:
                    optimization_display = "N/A"
                    optimization_class = "text-muted"

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
                    'optimization': optimization_display,
                    'optimization_class': optimization_class,
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
        day_of_week = date.weekday()
        from .models import Holiday
        is_holiday = Holiday.objects.filter(date=date, location='Gurgaon', is_active=True).exists()

        if is_holiday:
            default_status = 'HOLIDAY'
        elif day_of_week in [5, 6]:
            default_status = 'WEEK_OFF'
        else:
            default_status = 'PRESENT'

        # Let Django handle the database errors
        return DailyRoster.objects.get_or_create(
            team_member=team_member,
            date=date,
            defaults={
                'status': default_status,
                'is_auto_created': True
            }
        )
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
    def update_roster_status(team_member, date, new_status, misc_hours=None, misc_description=None, notes=None):
        """
        Update roster status and misc hours for a specific date.
        Now only updates fields that are explicitly provided.

        Args:
            team_member: User object
            date: Date object
            new_status: String status value
            misc_hours: Integer minutes for misc work. If None, it's not updated.
            misc_description: String description of misc work. If None, it's not updated.
            notes: String additional notes. If None, it's not updated.

        Returns:
            tuple: (success, result)
                - If successful: (True, roster_object)
                - If failed: (False, error_message)
        """
        with transaction.atomic():
            try:
                roster, created = ProjectService.get_or_create_daily_roster(team_member, date)


                # Update fields only if they are provided
                roster.status = new_status
                if misc_hours is not None:
                    roster.misc_hours = misc_hours
                if misc_description is not None:
                    roster.misc_description = misc_description
                if notes is not None:
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

    @staticmethod
    def get_team_member_projects(team_member):
        """
        Retrieves all projects where the team member is the project in-charge.
        Includes tasks and assignments for each project.

        Args:
            team_member: User object of the team member

        Returns:
            tuple: (success, result)
                - If successful: (True, projects_data)
                - If failed: (False, error_message)
        """
        try:
            # Get all projects where this team member is the project in-charge
            projects = Project.objects.filter(
                project_incharge=team_member
            ).select_related(
                'product',
                'city',
                'dpm',
                'current_status'
            ).prefetch_related(
                Prefetch(
                    'tasks',
                    queryset=ProjectTask.objects.select_related('product_task').prefetch_related(
                        Prefetch(
                            'assignments',
                            queryset=TaskAssignment.objects.select_related(
                                'assigned_to'
                            ).order_by('-assigned_date')
                        )
                    )
                )
            ).order_by('-created_at')

            # Process each project to add summary statistics
            projects_data = []
            for project in projects:
                # Calculate project-level task statistics
                total_tasks_in_project = project.tasks.count()
                completed_tasks_in_project = 0
                total_assignments_in_project = 0
                my_assignments_in_project = 0
                my_completed_assignments_in_project = 0

                # Prepare tasks with per-task statistics
                processed_tasks = []
                for task in project.tasks.all():
                    task_total_assignments = task.assignments.count()
                    task_completed_assignments = task.assignments.filter(is_completed=True).count()

                    # Determine if the task itself is completed (all its assignments are completed)
                    task_is_completed = (task_total_assignments > 0 and task_completed_assignments == task_total_assignments)
                    if task_is_completed:
                        completed_tasks_in_project += 1

                    # Accumulate project-level assignment counts
                    total_assignments_in_project += task_total_assignments
                    for assignment in task.assignments.all():
                        if assignment.assigned_to == team_member:
                            my_assignments_in_project += 1
                            if assignment.is_completed:
                                my_completed_assignments_in_project += 1

                    # Add calculated stats to the task object for template use
                    # We can dynamically add attributes to the task object before passing it
                    task.calculated_total_assignments = task_total_assignments
                    task.calculated_completed_assignments = task_completed_assignments
                    task.calculated_is_completed = task_is_completed # This flag will be used in template

                    processed_tasks.append(task) # Re-add the task with new attributes

                # Calculate project-level completion percentage
                completion_percentage = (completed_tasks_in_project / total_tasks_in_project * 100) if total_tasks_in_project > 0 else 0

                project_info = {
                    'project': project,
                    'stats': {
                        'total_tasks': total_tasks_in_project,
                        'completed_tasks': completed_tasks_in_project,
                        'completion_percentage': round(completion_percentage, 1),
                        'total_assignments': total_assignments_in_project,
                        'my_assignments': my_assignments_in_project,
                        'my_completed_assignments': my_completed_assignments_in_project,
                        'is_delivered': project.is_delivered,
                        'is_pipeline': project.is_pipeline
                    },
                    'processed_tasks': processed_tasks # Add the processed tasks list
                }

                projects_data.append(project_info)

            logger.debug(f"Retrieved {len(projects_data)} projects for team member {team_member.id}")
            return True, projects_data

        except Exception as e:
            logger.exception(f"Error retrieving team member projects: {str(e)}")
            return False, f"An error occurred: {str(e)}"

class ReportingService:
    """
    Simplified service layer for on-demand reporting.
    No more stored metrics - everything calculated fresh.
    """

    @staticmethod
    def get_team_member_metrics(team_member, start_date, end_date):
        """
        Calculate team member metrics on-demand for date range.
        Much simpler than the stored approach!
        """
        from decimal import Decimal
        from django.db.models import F, Case, When, IntegerField

        # Get completed assignments in date range
        completed_assignments = TaskAssignment.objects.filter(
            assigned_to=team_member,
            is_completed=True,
            completion_date__date__range=[start_date, end_date]
        ).select_related('task__project')

        # Get daily totals for utilization calculation
        daily_totals = DailyTimeTotal.objects.filter(
            team_member=team_member,
            date_worked__range=[start_date, end_date]
        ).values('date_worked').annotate(
            day_total=Sum('total_minutes')
        )

        # Get roster data for availability calculation
        roster_days = DailyRoster.objects.filter(
            team_member=team_member,
            date__range=[start_date, end_date]
        )

        # Calculate productivity metrics
        total_projected = 0
        total_worked = 0
        quality_ratings = []

        for assignment in completed_assignments:
            projected = assignment.projected_hours or 0
            worked = DailyTimeTotal.objects.filter(
                assignment=assignment,
                team_member=team_member
            ).aggregate(total=Sum('total_minutes'))['total'] or 0

            total_projected += projected
            total_worked += worked

            if assignment.quality_rating:
                quality_ratings.append(float(assignment.quality_rating))

        # Calculate utilization (total worked vs available time)
        total_available_minutes = 0
        total_worked_minutes = 0

        for roster in roster_days:
            if roster.status in ['PRESENT', 'LEAVE', 'HALF_DAY']:
                total_available_minutes += 480  # 8 hours

        total_worked_minutes = sum(dt['day_total'] for dt in daily_totals)

        # Calculate efficiency (assignment + misc hours vs present/half days only)
        efficiency_available_minutes = 0
        total_misc_minutes = 0

        for roster in roster_days:
            if roster.status == 'PRESENT':
                efficiency_available_minutes += 480  # 8 hours
            elif roster.status == 'HALF_DAY':
                efficiency_available_minutes += 240  # 4 hours

            # Add misc hours to total work time for efficiency calculation
            total_misc_minutes += roster.misc_hours

        total_efficiency_work_minutes = total_worked_minutes + total_misc_minutes

        # Calculate delivery performance
        deliveries = ProjectDelivery.objects.filter(
            project_incharge=team_member,
            delivery_date__range=[start_date, end_date]
        )

        delivery_ratings = [
            float(d.delivery_performance_rating)
            for d in deliveries
            if d.delivery_performance_rating
        ]

        # Calculate on-time delivery rate using database fields, not the property
        # A delivery is on-time if actual_completion_date <= expected_completion_date
        # Handle cases where expected_completion_date might be null
        on_time_deliveries = deliveries.filter(
            expected_completion_date__isnull=False
        ).filter(
            actual_completion_date__lte=F('expected_completion_date')
        )
        on_time_count = on_time_deliveries.count()
        total_deliveries = deliveries.count()

        return {
            'period': f"{start_date} to {end_date}",
            'productivity': {
                'score': (total_projected / total_worked * 100) if total_worked > 0 else None,
                'projected_hours': total_projected / 60,
                'worked_hours': total_worked / 60,
            },
            'optimization': {
                'score': ((total_projected - total_worked) / total_projected * 100) if total_projected > 0 else None,
                'projected_hours': total_projected / 60,
                'worked_hours': total_worked / 60,
                'saved_hours': (total_projected - total_worked) / 60 if total_projected > 0 else 0,
            },
            'utilization': {
                'score': (total_worked_minutes / total_available_minutes * 100) if total_available_minutes > 0 else None,
                'worked_minutes': total_worked_minutes,
                'available_minutes': total_available_minutes,
            },
            'efficiency': {
                'score': (total_efficiency_work_minutes / efficiency_available_minutes * 100) if efficiency_available_minutes > 0 else None,
                'total_work_minutes': total_efficiency_work_minutes,
                'assignment_minutes': total_worked_minutes,
                'misc_minutes': total_misc_minutes,
                'available_minutes': efficiency_available_minutes,
            },
            'quality': {
                'average_rating': sum(quality_ratings) / len(quality_ratings) if quality_ratings else None,
                'total_assignments': len(completed_assignments),
                'rated_assignments': len(quality_ratings),
            },
            'delivery': {
                'average_rating': sum(delivery_ratings) / len(delivery_ratings) if delivery_ratings else None,
                'total_projects': total_deliveries,
                'on_time_rate': (on_time_count / total_deliveries * 100) if total_deliveries > 0 else None,
                'on_time_count': on_time_count,
            }
        }

    @staticmethod
    def get_team_overview(start_date, end_date):
        """
        Get overview for all team members (much faster without stored metrics).
        """
        team_members = User.objects.filter(role='TEAM_MEMBER')
        overview_data = []

        for member in team_members:
            metrics = ReportingService.get_team_member_metrics(member, start_date, end_date)
            overview_data.append({
                'team_member': member,
                'metrics': metrics
            })

        # Sort by productivity
        overview_data.sort(
            key=lambda x: x['metrics']['productivity']['score'] or 0,
            reverse=True
        )

        return overview_data

    @staticmethod
    def get_daily_summary(team_member, date):
        """
        Get summary for a specific day - useful for dashboards.
        """
        # Today's worked time
        worked_minutes = DailyTimeTotal.objects.filter(
            team_member=team_member,
            date_worked=date
        ).aggregate(total=Sum('total_minutes'))['total'] or 0

        # Today's completed assignments
        completed_today = TaskAssignment.objects.filter(
            assigned_to=team_member,
            completion_date__date=date
        ).count()

        # Active assignments
        active_assignments = TaskAssignment.objects.filter(
            assigned_to=team_member,
            is_active=True,
            is_completed=False
        ).count()

        return {
            'worked_hours': f"{worked_minutes // 60:02d}:{worked_minutes % 60:02d}",
            'completed_assignments': completed_today,
            'active_assignments': active_assignments,
        }

    @staticmethod
    def track_project_delivery(project, delivery_date=None):
        """
        Simplified delivery tracking - just store the event, no metrics calculation.
        """
        if not delivery_date:
            delivery_date = date.today()

        if not project.project_incharge:
            return None

        # Check if already tracked
        existing = ProjectDelivery.objects.filter(
            project=project,
            delivery_date=delivery_date
        ).first()

        if existing:
            if project.delivery_performance_rating and existing.delivery_performance_rating != project.delivery_performance_rating:
                existing.delivery_performance_rating = project.delivery_performance_rating
                existing.save()
            return existing

        # Create delivery record
        delivery = ProjectDelivery.objects.create(
            project=project,
            project_incharge=project.project_incharge,
            delivery_date=delivery_date,
            delivery_performance_rating=project.delivery_performance_rating,
            project_name=project.project_name,
            hs_id=project.hs_id,
            expected_completion_date=project.expected_completion_date,
            actual_completion_date=delivery_date
        )

        return delivery