#projects/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProjectStatusUpdateForm, ProjectFilterForm, ProjectCreateForm, ProjectTaskForm, TaskAssignmentForm, TaskAssignmentUpdateForm, ProjectManagementForm, AddMiscHoursForm, TimerStopForm, ManualTimeEntryForm, EditSessionDurationForm, DailyRosterFilterForm
from .services import ProjectService
from accounts.models import User
from locations.models import Region, City
from django.http import JsonResponse
from .models import Project, ProjectStatusOption, ProjectTask, TaskAssignment, ProjectStatusHistory, ActiveTimer, TimeSession, DailyTimeTotal, ProjectDelivery
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Subquery, OuterRef, F, Avg, Count, Q
from django.core.exceptions import ValidationError
import uuid
from datetime import date, timedelta, datetime
from django.utils import timezone
import json




def ensure_is_dpm(request, project):
    """
    Verify that the current user is a DPM.

    Args:
        request: The HTTP request
        project: The project object (used for redirect)

    Returns:
        Response or None: Redirect response if check fails, None if successful
    """
    if request.user.role != 'DPM':
        messages.error(request, "Only a DPM can perform this action.")
        return redirect('projects:project_detail', project_id=project.id)
    return None

@login_required
def create_project(request):
    """
    View for creating a new project. Handles form processing and
    delegates business logic to the service layer.
    Only accessible by DPMs.
    """
    # Check if user is a DPM
    if request.user.role != 'DPM':
        messages.error(request, "Access denied. Only Project Managers can create projects.")
        return redirect('home')
    
    if request.method == 'POST':
        # Create and validate form
        form = ProjectCreateForm(request.POST, user=request.user)

        if form.is_valid():
            try:
                # Form's save method delegates to service
                project = form.save()
                messages.success(request, f'Project "{project.project_name}" has been created successfully.')
                return redirect('projects:project_detail', project_id=project.id)
            except ValidationError as e:
                # Handle service-layer validation errors
                messages.error(request, f"Error creating project: {e}")
        else:
            # Form validation failed
            messages.error(request, "Please correct the errors below.")
    else:
        # For GET requests, create an empty form
        form = ProjectCreateForm(user=request.user)

    # Render the template with the form
    return render(request, 'projects/create_project.html', {'form': form, 'title': 'Create New Project'})


@login_required
def project_detail(request, project_id):
    """Display detailed information about a specific project. Only accessible by DPMs."""
    # Check if user is a DPM first
    if request.user.role != 'DPM':
        messages.error(request, "Access denied. Only Project Managers can view project details.")
        return redirect('home')
    
    # Get project data using appropriate service methods
    success, result = ProjectService.get_project_details(project_id)
    if not success:
        messages.error(request, result)
        return redirect('projects:project_list')

    project, status_history = result

    # Get status options for the modal
    status_options = ProjectStatusOption.objects.filter(is_active=True).order_by('order')

    # Prepare the form for the modal
    form = ProjectStatusUpdateForm(initial={'status': project.current_status})

    # Prepare context
    context = {
        'project': project,
        'status_history': status_history,
        'status_options': status_options,
        'form': form,
        'title': f'Project: {project.project_name}'
    }

    return render(request, 'projects/project_detail.html', context)

@login_required
def update_project_status(request, project_id):
    """
    Handle status updates for a project.
    Now supports both regular and AJAX requests.
    Only accessible by DPMs.
    """
    # Check if user is a DPM first
    if request.user.role != 'DPM':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied. Only Project Managers can update project status.'}, status=403)
        messages.error(request, "Access denied. Only Project Managers can update project status.")
        return redirect('home')
    
    # Get the project first
    success, result = ProjectService.get_project(project_id)

    if not success:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': result}, status=404)
        messages.error(request, result)
        return redirect('projects:project_list')

    project = result

    # Check if it's an AJAX request to get status options
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return available status options as JSON
        statuses = ProjectStatusOption.objects.filter(is_active=True).order_by('order')
        status_options = [{'id': str(s.id), 'name': s.name} for s in statuses]
        return JsonResponse({'status_options': status_options})

    if request.method == 'POST':
        form = ProjectStatusUpdateForm(request.POST)
        if form.is_valid():
            status_id = form.cleaned_data['status'].id
            comments = form.cleaned_data['comments']

            success, result = ProjectService.update_project_status(
                project_id=project_id,
                status_id=status_id,
                user=request.user,
                comments=comments
            )

            if success:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Project status updated successfully.',
                        'new_status': result.current_status.name
                    })
                messages.success(request, "Project status updated successfully.")
                return redirect('projects:project_detail', project_id=project_id)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': result}, status=400)
                messages.error(request, result)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return form errors as JSON
                errors = {}
                for field, field_errors in form.errors.items():
                    errors[field] = list(field_errors)
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            messages.error(request, "Please correct the form errors.")
    else:
        # Pre-select current status in form
        form = ProjectStatusUpdateForm(initial={'status': project.current_status})

    # For non-AJAX requests, render the original template
    return render(request, 'projects/status_update.html', {
        'form': form,
        'project': project,
        'title': f'Update Status: {project.project_name}'
    })


@login_required
def project_list(request):
    """
    Displays a filterable list of pipeline projects (not yet delivered).
    Only accessible by DPMs.
    """
    # Check if user is a DPM
    if request.user.role != 'DPM':
        messages.error(request, "Access denied. This page is only for Project Managers.")
        return redirect('home')
    
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    product = request.GET.get('product', '')
    region = request.GET.get('region', '')
    city = request.GET.get('city', '')
    dpm = request.GET.get('dpm', '')
    page = request.GET.get('page', 1)

    # Get pipeline projects using service (exclude Final Delivery status)
    success, result = ProjectService.get_project_list(
        search_query=search_query,
        status=status,
        product=product,
        region=region,
        city=city,
        dpm=dpm,
        page=page,
        project_type='pipeline'  # Only get pipeline projects
    )

    if not success:
        messages.error(request, result)
        return redirect('home')

    projects, filters_applied = result

    # Get filter options
    success, filter_options_result = ProjectService.get_filter_options()
    if not success:
        messages.warning(request, filter_options_result)
        filter_options = {
            'statuses': [],
            'products': [],
            'cities': [],
            'regions': [],
            'dpms': []
        }
    else:
        filter_options = filter_options_result

    # Create filter form with current values
    filter_form = ProjectFilterForm(initial=filters_applied)

    # Update city queryset based on selected region
    if region:
        filter_form.fields['city'].queryset = City.objects.filter(region_id=region)

    # Get display names for applied filters for the template
    filters_applied_display = {}
    if filters_applied.get('status'):
        try:
            filters_applied_display['status'] = ProjectStatusOption.objects.get(id=filters_applied['status']).name
        except ProjectStatusOption.DoesNotExist:
            pass
    if filters_applied.get('product'):
        try:
            filters_applied_display['product'] = Product.objects.get(id=filters_applied['product']).name
        except Product.DoesNotExist:
            pass
    if filters_applied.get('region'):
        try:
            filters_applied_display['region'] = Region.objects.get(id=filters_applied['region']).name
        except Region.DoesNotExist:
            pass
    if filters_applied.get('city'):
        try:
            filters_applied_display['city'] = City.objects.get(id=filters_applied['city']).name
        except City.DoesNotExist:
            pass
    if filters_applied.get('dpm'):
        try:
            dpm_user = User.objects.get(id=filters_applied['dpm'])
            filters_applied_display['dpm'] = dpm_user.get_full_name() or dpm_user.username
        except User.DoesNotExist:
            pass

    context = {
        'projects': projects,
        'filter_form': filter_form,
        'filters_applied': filters_applied,
        'filters_applied_display': filters_applied_display,
        'filter_options': filter_options,
        'title': 'Pipeline Projects',
        'is_pipeline': True  # Add flag to identify page type
    }

    return render(request, 'projects/project_list.html', context)


@login_required
def delivered_projects(request):
    """
    Displays a filterable list of delivered projects (Final Delivery status).
    Only accessible by DPMs.
    """
    # Check if user is a DPM
    if request.user.role != 'DPM':
        messages.error(request, "Access denied. This page is only for Project Managers.")
        return redirect('home')
    
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    product = request.GET.get('product', '')
    region = request.GET.get('region', '')
    city = request.GET.get('city', '')
    dpm = request.GET.get('dpm', '')
    page = request.GET.get('page', 1)

    # Get delivered projects using service
    success, result = ProjectService.get_project_list(
        search_query=search_query,
        status=status,
        product=product,
        region=region,
        city=city,
        dpm=dpm,
        page=page,
        project_type='delivered'  # Only get delivered projects
    )

    if not success:
        messages.error(request, result)
        return redirect('home')

    projects, filters_applied = result

    # Get filter options
    success, filter_options_result = ProjectService.get_filter_options()
    if not success:
        messages.warning(request, filter_options_result)
        filter_options = {
            'statuses': [],
            'products': [],
            'cities': [],
            'regions': [],
            'dpms': []
        }
    else:
        filter_options = filter_options_result

    # Create filter form with current values
    filter_form = ProjectFilterForm(initial=filters_applied)

    # Update city queryset based on selected region
    if region:
        filter_form.fields['city'].queryset = City.objects.filter(region_id=region)

    # Get display names for applied filters
    filters_applied_display = {}
    if filters_applied.get('status'):
        try:
            filters_applied_display['status'] = ProjectStatusOption.objects.get(id=filters_applied['status']).name
        except ProjectStatusOption.DoesNotExist:
            pass
    if filters_applied.get('product'):
        try:
            filters_applied_display['product'] = Product.objects.get(id=filters_applied['product']).name
        except Product.DoesNotExist:
            pass
    if filters_applied.get('region'):
        try:
            filters_applied_display['region'] = Region.objects.get(id=filters_applied['region']).name
        except Region.DoesNotExist:
            pass
    if filters_applied.get('city'):
        try:
            filters_applied_display['city'] = City.objects.get(id=filters_applied['city']).name
        except City.DoesNotExist:
            pass
    if filters_applied.get('dpm'):
        try:
            dpm_user = User.objects.get(id=filters_applied['dpm'])
            filters_applied_display['dpm'] = dpm_user.get_full_name() or dpm_user.username
        except User.DoesNotExist:
            pass

    context = {
        'projects': projects,
        'filter_form': filter_form,
        'filters_applied': filters_applied,
        'filters_applied_display': filters_applied_display,
        'filter_options': filter_options,
        'title': 'Delivered Projects',
        'is_delivered': True  # Add flag to identify page type
    }

    return render(request, 'projects/delivered_projects.html', context)


def get_cities(request):
    """
    API endpoint to get cities for a specific region.
    Used by the dynamic city dropdown in the filter form.
    """
    region_id = request.GET.get('region')
    if region_id:
        cities = City.objects.filter(region_id=region_id).values('id', 'name')
        return JsonResponse(list(cities), safe=False)
    return JsonResponse([], safe=False)


@login_required
def project_management(request, project_id):
    """Display project management page with forms and tasks."""
    # Get project for permission check
    success, result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, result)
        return redirect('projects:project_list')

    project = result

    # Use the permission helper function
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Get project with tasks using the service method
    success, result = ProjectService.get_project_with_tasks(project_id)

    if not success:
        messages.error(request, result)
        return redirect('projects:project_list')

    # Unpack the result tuple
    project, tasks = result

    # Prepare context
    context = {
        'project': project,
        'tasks': tasks,
        'title': f'Manage Project: {project.project_name}',
        'project_form': ProjectManagementForm(instance=project),
        'task_form': ProjectTaskForm(project=project)
    }

    return render(request, 'projects/project_management.html', context)


@login_required
def create_project_task(request, project_id):
    """Handle task creation only."""
    if request.method != 'POST':
        return redirect('projects:project_management', project_id=project_id)

    # Get project to check configuration
    success, result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, result)
        return redirect('projects:project_list')

    project = result

    # Check if user is the DPM
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Check project configuration before attempting task creation
    if not project.project_incharge or not project.expected_completion_date:
        messages.warning(
            request,
            "Please complete the project configuration before creating tasks."
        )
        return redirect('projects:project_management', project_id=project_id)

    # Process form in the view
    form = ProjectTaskForm(project=project, user=request.user, data=request.POST)

    if form.is_valid():
        try:
            # Form's save method delegates to service
            form.save()
            messages.success(request, "Task created successfully")
        except ValidationError as e:
            messages.error(request, f"Error creating task: {e}")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('projects:project_management', project_id=project_id)


@login_required
def update_project_configuration(request, project_id):
    """Handle project configuration updates only."""
    if request.method != 'POST':
        return redirect('projects:project_management', project_id=project_id)

    # Get project to check permissions
    success, result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, result)
        return redirect('projects:project_list')

    project = result

    # Check if user is the DPM
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Process form in the view
    form = ProjectManagementForm(request.POST, instance=project)

    if form.is_valid():
        # Pass cleaned data to service
        success, result = ProjectService.update_project_configuration(
            project_id=project_id,
            config_data=form.cleaned_data,
            dpm=request.user
        )

        if success:
            messages.success(request, "Project details updated successfully")

            # Check if delivery performance rating was updated
            if 'delivery_performance_rating' in form.changed_data:
                # Update any existing ProjectDelivery records
                from projects.models import ProjectDelivery
                ProjectDelivery.objects.filter(project=project).update(
                    delivery_performance_rating=form.cleaned_data['delivery_performance_rating']
                )

                # Recalculate metrics if there are deliveries
                deliveries = ProjectDelivery.objects.filter(project=project)
                for delivery in deliveries:
                    ProjectService.calculate_team_member_metrics(
                        delivery.project_incharge,
                        delivery.delivery_date
                    )
        else:
            messages.error(request, result)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('projects:project_management', project_id=project_id)



@login_required
def task_detail(request, project_id, task_id):
    """Display task details and assignment list."""
    # Get the project
    success, project_result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, project_result)
        return redirect('projects:project_list')

    project = project_result

    # Check if user is the DPM
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Get task and assignments
    success, task_result = ProjectService.get_task_with_assignments(task_id)
    if not success:
        messages.error(request, task_result)
        return redirect('projects:project_management', project_id=project_id)

    task, assignments = task_result

    # Ensure task belongs to the correct project
    if task.project.id != project.id:
        messages.error(request, "Invalid task for this project")
        return redirect('projects:project_management', project_id=project_id)

    # Separate assignments into active and completed
    active_assignments = []
    completed_assignments = []

    for assignment in assignments:
        # Add working hours to each assignment
        assignment.working_hours = assignment.get_total_working_hours()

        if assignment.is_completed:
            completed_assignments.append(assignment)
        else:
            active_assignments.append(assignment)

    # Prepare context
    context = {
        'task': task,
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
        'project': project,
        'title': f'Task: {task.task_id}',
        'assignment_form': TaskAssignmentForm(),
        'update_form': TaskAssignmentUpdateForm()
    }

    return render(request, 'projects/task_detail.html', context)


@login_required
def create_task_assignment(request, project_id, task_id):
    """Handle new assignment creation."""
    if request.method != 'POST':
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Get the project and check permissions
    success, project_result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, project_result)
        return redirect('projects:project_list')

    project = project_result
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Get the task to pass to the form
    success, task_result = ProjectService.get_project_task(task_id, project_id)
    if not success:
        messages.error(request, task_result)
        return redirect('projects:project_management', project_id=project_id)

    task = task_result

    # Use the form for validation and data conversion
    form = TaskAssignmentForm(data=request.POST, task=task, user=request.user)

    if form.is_valid():
        try:
            # Form's save method delegates to service
            form.save()
            messages.success(request, "Assignment created successfully")
        except ValidationError as e:
            messages.error(request, f"Error creating assignment: {e}")

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('projects:task_detail', project_id=project_id, task_id=task_id)


@login_required
def update_task_assignment(request, project_id, task_id, assignment_id):
    """Handle assignment updates."""
    if request.method != 'POST':
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Get the project and perform permission checks
    success, project_result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, project_result)
        return redirect('projects:project_list')

    project = project_result
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # First get the current assignment
    success, assignment_result = ProjectService.get_task_assignment(assignment_id)
    if not success:
        messages.error(request, assignment_result)
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    assignment = assignment_result

    # Add validation that assignment belongs to the correct task and project
    if assignment.task.id != task_id or assignment.task.project.id != project_id:
        messages.error(request, "Invalid assignment for this project and task")
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Use the form to validate and convert the data
    form = TaskAssignmentUpdateForm(data=request.POST, instance=assignment)

    if form.is_valid():
        # Form is valid, get the cleaned_data which has proper conversions applied
        form_data = form.cleaned_data

        # Pass the properly converted data to the service
        success, result = ProjectService.update_task_assignment(
            assignment_id=assignment_id,
            assignment_data=form_data,
            dpm=request.user
        )

        if success:
            messages.success(request, "Assignment updated successfully")
        else:
            messages.error(request, result)
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('projects:task_detail', project_id=project_id, task_id=task_id)


@login_required
def dpm_task_dashboard(request):
    """
    Dashboard view for DPMs showing their projects for task management.
    This is the new Task Management tab for DPMs.
    """
    # Redirect non-DPM users to appropriate page
    if request.user.role != 'DPM':
        messages.error(request, "Access denied. This page is only for Project Managers.")
        return redirect('home')

    # Get projects for this DPM
    success, result = ProjectService.get_dpm_projects_for_task_management(request.user)

    if not success:
        messages.error(request, result)
        return redirect('home')

    projects = result

    context = {
        'projects': projects,
        'title': 'Task Management Dashboard'
    }

    return render(request, 'projects/dpm_task_dashboard.html', context)


@login_required
def team_member_dashboard(request):
    """
    Enhanced dashboard view for team members with timer functionality.
    Handles timer start/stop, manual time entry, and assignment completion.
    """
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "This dashboard is only for team members")
        return redirect('projects:project_list')

    # Handle POST requests (timer actions)
    if request.method == 'POST':

        # Start Timer
        if 'start_timer' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            success, result = ProjectService.start_timer(assignment_id, request.user)

            if success:
                messages.success(request, f"Timer started for assignment {result.assignment.assignment_id}")
            else:
                messages.error(request, result)

        # Stop Timer
        elif 'stop_timer' in request.POST:
            form = TimerStopForm(request.POST)
            if form.is_valid():
                description = form.cleaned_data['description']
                is_completed = form.cleaned_data['is_completed']

                success, result = ProjectService.stop_timer(request.user, description)

                if success:
                    messages.success(request, f"Timer stopped. Session duration: {result.get_formatted_duration()}")

                    # Mark as completed if requested
                    if is_completed:
                        success, complete_result = ProjectService.complete_assignment(
                            result.assignment.id,
                            request.user
                        )
                        if success:
                            messages.success(request, f"Assignment {complete_result.assignment_id} marked as completed!")
                        else:
                            messages.warning(request, f"Timer stopped but couldn't complete assignment: {complete_result}")
                else:
                    messages.error(request, result)

        # Add Manual Time
        elif 'add_time' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            form = ManualTimeEntryForm(request.POST)

            if form.is_valid():
                success, result = ProjectService.add_manual_time(
                    assignment_id=assignment_id,
                    team_member=request.user,
                    date_worked=form.cleaned_data['date'],
                    hours=form.cleaned_data['duration_hours'],
                    minutes=form.cleaned_data['duration_minutes'],
                    description=form.cleaned_data['description']
                )

                if success:
                    total_minutes = (form.cleaned_data['duration_hours'] * 60) + form.cleaned_data['duration_minutes']
                    messages.success(request, f"Added {ProjectService._format_minutes(total_minutes)} to your timesheet")

                    # Mark as completed if requested
                    if form.cleaned_data['is_completed']:
                        success, complete_result = ProjectService.complete_assignment(assignment_id, request.user)
                        if success:
                            messages.success(request, f"Assignment {complete_result.assignment_id} marked as completed!")
                        else:
                            messages.warning(request, f"Time added but couldn't complete assignment: {complete_result}")
                else:
                    messages.error(request, result)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

        # Mark Completed
        elif 'mark_completed' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            success, result = ProjectService.complete_assignment(assignment_id, request.user)

            if success:
                messages.success(request, f"Assignment {result.assignment_id} marked as completed!")
            else:
                messages.error(request, result)

        # Redirect to prevent form resubmission
        return redirect('projects:team_member_dashboard')

    # GET request - display dashboard
    success, result = ProjectService.get_team_member_dashboard_data(request.user)

    if not success:
        messages.error(request, result)
        return redirect('home')

    dashboard_data = result

    # Create forms for the modals
    timer_stop_form = TimerStopForm()
    time_entry_form = ManualTimeEntryForm()

    context = {
        'active_assignments': dashboard_data['active_assignments'],
        'completed_assignments': dashboard_data['completed_assignments'],
        'active_timer': dashboard_data['active_timer'],
        'elapsed_time': dashboard_data['elapsed_time'],
        'today_summary': dashboard_data['today_summary'],
        'timer_stop_form': timer_stop_form,
        'time_entry_form': time_entry_form,
        'title': 'My Tasks Dashboard',
        'now': timezone.now()  # For template comparisons
    }

    return render(request, 'projects/team_member_dashboard.html', context)


@login_required
def completed_assignments_list(request):
    """
    Display completed assignments for the current team member with optional date filtering.
    """
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "This page is only accessible by team members")
        return redirect('projects:project_list')

    # Get date range parameters from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Parse dates if provided
    start_date = None
    end_date = None
    date_filter_active = False

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            date_filter_active = True
        except ValueError:
            messages.warning(request, "Invalid start date format")

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_filter_active = True
        except ValueError:
            messages.warning(request, "Invalid end date format")

    # Validate date range
    if start_date and end_date and start_date > end_date:
        messages.error(request, "Start date cannot be after end date")
        start_date = end_date = None
        date_filter_active = False

    # Get completed assignments with date filtering
    success, result = ProjectService.get_team_member_all_completed_assignments(
        request.user, start_date, end_date
    )

    if not success:
        messages.error(request, result)
        return redirect('projects:team_member_dashboard')

    completed_assignments = result

    # Prepare filter display text
    filter_text = "All Time"
    if date_filter_active:
        if start_date and end_date:
            filter_text = f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"
        elif start_date:
            filter_text = f"From {start_date.strftime('%b %d, %Y')}"
        elif end_date:
            filter_text = f"Until {end_date.strftime('%b %d, %Y')}"

    context = {
        'completed_assignments': completed_assignments,
        'title': 'Completed Assignments',
        'total_count': len(completed_assignments),
        'start_date': start_date_str or '',
        'end_date': end_date_str or '',
        'filter_text': filter_text,
        'date_filter_active': date_filter_active
    }

    return render(request, 'projects/completed_assignments_list.html', context)


@login_required
def assignment_timesheet(request, assignment_id):
    """View detailed timesheet for a specific assignment."""
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "Access denied")
        return redirect('home')

    # Handle session duration editing
    if request.method == 'POST' and 'edit_session_duration' in request.POST:
        # Get form data
        form_data = {
            'session_id': request.POST.get('session_id'),
            'duration_hours': request.POST.get('duration_hours'),
            'duration_minutes': request.POST.get('duration_minutes')
        }

        # Create and validate form
        form = EditSessionDurationForm(form_data)

        if form.is_valid():
            session_id = form.cleaned_data['session_id']
            total_minutes = form.get_total_minutes()

            # Call service method
            success, result = ProjectService.edit_session_duration(
                session_id=session_id,
                team_member=request.user,
                new_duration_minutes=total_minutes
            )

            if success:
                formatted_duration = ProjectService._format_minutes(total_minutes)
                messages.success(request, f"Session duration updated to {formatted_duration}")
            else:
                messages.error(request, f"Error updating session: {result}")
        else:
            # Handle form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('projects:assignment_timesheet', assignment_id=assignment_id)

    # Get timesheet data using service layer (no date filtering)
    success, result = ProjectService.get_assignment_timesheet_data(
        assignment_id, request.user
    )

    if not success:
        messages.error(request, result)
        return redirect('projects:team_member_dashboard')

    timesheet_data = result

    context = {
        'assignment': timesheet_data['assignment'],
        'daily_totals': timesheet_data['daily_totals'],
        'sessions': timesheet_data['sessions'],
        'assignment_summary': timesheet_data['assignment_summary'],
        'title': f'Timesheet: {timesheet_data["assignment"].assignment_id}'
    }

    return render(request, 'projects/assignment_timesheet.html', context)

@login_required
def daily_roster(request):
    """View team member's daily time breakdown."""
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "Access denied")
        return redirect('home')

    # Get filter form
    filter_form = DailyRosterFilterForm(request.GET)

    # Default to today
    selected_date = date.today()
    show_week = False

    if filter_form.is_valid():
        if filter_form.cleaned_data['date']:
            selected_date = filter_form.cleaned_data['date']
        show_week = filter_form.cleaned_data.get('week_view', False)

    # ✅ NOW USING SERVICE LAYER:
    success, result = ProjectService.get_daily_roster_data(
        request.user, selected_date, show_week
    )

    if not success:
        messages.error(request, result)
        return redirect('home')

    roster_data = result

    context = {
        'daily_totals': roster_data['daily_totals'],
        'filter_form': filter_form,
        'selected_date': selected_date,
        'show_week': show_week,
        'date_range': roster_data['date_range'],
        'total_formatted': roster_data['total_formatted'],
        'title': f'Daily Roster - {roster_data["date_range"]}'
    }

    return render(request, 'projects/daily_roster.html', context)

@login_required
def monthly_roster(request, year=None, month=None):
    """
    Display monthly roster for team member.
    Shows calendar view with daily status and hours.
    Now includes misc hours functionality.
    """
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "This page is only for team members")
        return redirect('home')

    # Handle misc hours addition
    if request.method == 'POST' and 'add_misc_hours' in request.POST:
        form = AddMiscHoursForm(request.POST)

        if form.is_valid():
            success, result = ProjectService.add_misc_hours(
                team_member=request.user,
                work_date=form.cleaned_data['date'],
                activity=form.cleaned_data['activity'],
                duration_hours=form.cleaned_data['duration_hours'],
                duration_minutes=form.cleaned_data['duration_minutes']
            )

            if success:
                total_minutes = form.get_total_minutes()
                formatted_duration = ProjectService._format_minutes(total_minutes)
                messages.success(request, f"Added {formatted_duration} of misc work: {form.cleaned_data['activity']}")
            else:
                messages.error(request, f"Error adding misc hours: {result}")
        else:
            # Handle form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        # Redirect to the same month after processing
        if year and month:
            return redirect('projects:roster_date', year=year, month=month)  # FIXED: Changed from 'monthly_roster_date'
        else:
            return redirect('projects:roster')  # FIXED: Changed from 'monthly_roster'

    # Default to current month if not specified
    if not year or not month:
        today = date.today()
        year, month = today.year, today.month

    # Get monthly roster data
    success, result = ProjectService.get_monthly_roster(request.user, year, month)

    if not success:
        messages.error(request, result)
        return redirect('projects:team_member_dashboard')

    monthly_data = result

    # Calculate navigation dates
    current_date = date(year, month, 1)
    prev_month = current_date - timedelta(days=1)
    next_month_day = current_date.replace(day=28) + timedelta(days=4)
    next_month = next_month_day - timedelta(days=next_month_day.day-1)

    # Create misc hours form for the modal
    misc_hours_form = AddMiscHoursForm()

    context = {
        'monthly_data': monthly_data,
        'current_date': current_date,
        'prev_month': prev_month,
        'next_month': next_month,
        'misc_hours_form': misc_hours_form,
        'title': f'Roster - {monthly_data["month_name"]} {year}'
    }

    return render(request, 'projects/monthly_roster.html', context)

@login_required
def update_roster_day(request):
    """
    Update roster status for a specific day.
    """
    if request.user.role != 'TEAM_MEMBER':
        messages.error(request, "Access denied")
        return redirect('home')

    if request.method != 'POST':
        return redirect('projects:roster')  # FIXED: Changed from 'monthly_roster'

    try:
        # Get form data
        date_str = request.POST.get('date')
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        # Parse date
        from datetime import datetime
        work_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Get existing roster to preserve misc hours and description
        roster, _ = ProjectService.get_or_create_daily_roster(request.user, work_date)

        # Update roster using service
        success, result = ProjectService.update_roster_status(
            team_member=request.user,
            date=work_date,
            new_status=new_status,
            misc_hours=roster.misc_hours,
            misc_description=roster.misc_description,
            notes=notes
        )

        if success:
            messages.success(request, f"Status updated for {work_date.strftime('%B %d, %Y')}")
        else:
            messages.error(request, f"Error updating status: {result}")

    except Exception as e:
        messages.error(request, f"Invalid date format: {str(e)}")

    # Redirect back to the same month
    try:
        work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        return redirect('projects:roster_date', year=work_date.year, month=work_date.month)
    except:
        return redirect('projects:roster')


@login_required
def update_quality_rating(request, project_id, task_id, assignment_id):
    """
    Dedicated view for updating only the quality rating of completed assignments.
    Bypasses the complex TaskAssignmentUpdateForm validation.
    """
    if request.method != 'POST':
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Get the project and check permissions
    success, project_result = ProjectService.get_project(project_id)
    if not success:
        messages.error(request, project_result)
        return redirect('projects:project_list')

    project = project_result
    redirect_response = ensure_is_dpm(request, project)
    if redirect_response:
        return redirect_response

    # Get the assignment
    success, assignment_result = ProjectService.get_task_assignment(assignment_id)
    if not success:
        messages.error(request, assignment_result)
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    assignment = assignment_result

    # Validate assignment belongs to correct task and project
    if assignment.task.id != task_id or assignment.task.project.id != project_id:
        messages.error(request, "Invalid assignment for this project and task")
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Validate assignment is completed
    if not assignment.is_completed:
        messages.error(request, "Can only rate quality of completed assignments")
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    # Get and validate quality rating
    quality_rating = request.POST.get('quality_rating')
    if not quality_rating:
        messages.error(request, "Please select a quality rating")
        return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

    try:
        # Convert to decimal and validate range
        rating_value = float(quality_rating)
        if rating_value < 1.0 or rating_value > 5.0:
            messages.error(request, "Quality rating must be between 1.0 and 5.0")
            return redirect('projects:task_detail', project_id=project_id, task_id=task_id)

        # Update only the quality rating
        assignment.quality_rating = rating_value
        assignment.save()

        messages.success(request, f"Quality rating updated to {rating_value}/5 for assignment {assignment.assignment_id}")

    except (ValueError, TypeError):
        messages.error(request, "Invalid quality rating value")

    return redirect('projects:task_detail', project_id=project_id, task_id=task_id)



@login_required
def my_projects(request):
    """
    Display all projects where the current user is the project in-charge.
    This is a read-only view for team members.
    """
    # Check if user is a team member
    if request.user.role != 'TEAM_MEMBER':
        messages.warning(request, "This view is only available for team members.")
        return redirect('home')

    # Get projects where user is project in-charge
    success, result = ProjectService.get_team_member_projects(request.user)

    if not success:
        messages.error(request, result)
        return redirect('projects:team_member_dashboard')

    projects_data = result

    # Separate pipeline and delivered projects
    pipeline_projects = [p for p in projects_data if p['stats']['is_pipeline']]
    delivered_projects = [p for p in projects_data if p['stats']['is_delivered']]

    context = {
        'projects_data': projects_data,
        'pipeline_projects': pipeline_projects,
        'delivered_projects': delivered_projects,
        'title': 'My Projects',
        'total_projects': len(projects_data),
        'is_read_only': True  # Flag to ensure read-only display
    }

    return render(request, 'projects/my_projects.html', context)


@login_required
def delivery_performance_report(request):
    """
    View for delivery performance across all project incharges.
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=90)  # Last 3 months

    # Get all team members who have been project incharge
    team_members_with_deliveries = User.objects.filter(
        project_deliveries__delivery_date__range=[start_date, end_date]
    ).distinct()

    # Build report data
    report_data = []
    for member in team_members_with_deliveries:
        deliveries = ProjectDelivery.objects.filter(
            project_incharge=member,
            delivery_date__range=[start_date, end_date]
        )

        metrics = deliveries.aggregate(
            avg_rating=Avg('delivery_performance_rating'),
            total_projects=Count('id'),
            on_time=Count('id', filter=Q(days_variance__lte=0)),
            late=Count('id', filter=Q(days_variance__gt=0))
        )

        report_data.append({
            'team_member': member,
            'average_rating': metrics['avg_rating'],
            'total_deliveries': metrics['total_projects'],
            'on_time_rate': (metrics['on_time'] / metrics['total_projects'] * 100) if metrics['total_projects'] > 0 else 0,
            'deliveries': deliveries[:5]  # Recent 5
        })

    # Sort by average rating
    report_data.sort(key=lambda x: x['average_rating'] or 0, reverse=True)

    context = {
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Delivery Performance Report'
    }

    return render(request, 'projects/reports/delivery_performance.html', context)