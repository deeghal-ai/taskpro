from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from .models import VideoProject
from .services import VideoProjectService
from .forms import (
    VideoProjectCreateForm, VideoProjectStatusUpdateForm, VideoProjectFilterForm,
    VideoCutSubmissionForm, VoiceoverScriptForm, VideoCutFeedbackForm, VideoProjectEditForm
)

def ensure_is_video_pm(user):
    """Helper function to check VIDEO_PM role"""
    if user.role != 'VIDEO_PM':
        raise PermissionDenied("Access denied. Video Production Manager role required.")

@login_required
def video_create_project(request):
    """Create new video production project - VIDEO_PM only"""
    ensure_is_video_pm(request.user)
    
    if request.method == 'POST':
        form = VideoProjectCreateForm(request.POST)
        if form.is_valid():
            try:
                project = VideoProjectService.create_video_project(
                    form.cleaned_data, 
                    request.user
                )
                messages.success(request, f'Video project "{project.project_name}" created successfully with ID: {project.hs_id}')
                return redirect('video_production:project_detail', project_id=project.id)
            except IntegrityError as e:
                messages.error(request, f'Error creating project: {str(e)}')
            except ValueError as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VideoProjectCreateForm()
    
    return render(request, 'video_production/video_create_project.html', {
        'form': form,
        'page_title': 'Create Video Production Project'
    })

@login_required
def video_project_detail(request, project_id):
    """View video project details with cuts and voiceover history"""
    ensure_is_video_pm(request.user)
    
    try:
        project_details = VideoProjectService.get_video_project_details(project_id)
        
        # Check if user owns this project
        if project_details['project'].video_pm != request.user:
            raise PermissionDenied("You can only view your own projects.")
        
        return render(request, 'video_production/video_project_detail.html', {
            'project': project_details['project'],
            'cuts': project_details['cuts'],
            'voiceover_scripts': project_details['voiceover_scripts'],
            'status_history': project_details['status_history'],
            'delivery': project_details['delivery'],
            'page_title': f'Video Project - {project_details["project"].hs_id}'
        })
    except VideoProject.DoesNotExist:
        messages.error(request, 'Video project not found.')
        return redirect('video_production:project_list')

@login_required
@require_http_methods(["POST"])
def video_update_project_status(request, project_id):
    """Update project status - supports AJAX"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only update your own projects.")
        
        form = VideoProjectStatusUpdateForm(request.POST)
        if form.is_valid():
            updated_project = VideoProjectService.update_video_project_status(
                project_id,
                form.cleaned_data['status'].id,
                form.cleaned_data['comments'],
                request.user
            )
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': f'Status updated to {updated_project.current_status.name}',
                    'new_status': updated_project.current_status.name
                })
            else:
                messages.success(request, f'Project status updated to {updated_project.current_status.name}')
                return redirect('video_production:project_detail', project_id=project_id)
        else:
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
            else:
                messages.error(request, 'Error updating status. Please check your input.')
                return redirect('video_production:project_detail', project_id=project_id)
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        else:
            messages.error(request, str(e))
            return redirect('video_production:project_list')

@login_required
def video_project_list(request):
    """List pipeline (active) video projects"""
    ensure_is_video_pm(request.user)
    
    # Get filter form
    filter_form = VideoProjectFilterForm(request.GET or None)
    
    # Get projects with filters
    filters = {}
    if filter_form.is_valid():
        for field_name, value in filter_form.cleaned_data.items():
            if value:
                filters[field_name] = value
    
    # Get projects based on filters
    if filters:
        projects_queryset = VideoProjectService.get_video_project_list(request.user, filters)
    else:
        projects_queryset = VideoProjectService.get_pipeline_projects(request.user)
    
    # Pagination
    paginator = Paginator(projects_queryset, 10)  # 10 projects per page
    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)
    
    # Get filter options for form
    filter_options = VideoProjectService.get_video_filter_options()
    
    return render(request, 'video_production/video_project_list.html', {
        'projects': projects,
        'filter_form': filter_form,
        'filter_options': filter_options,
        'page_title': 'Video Production Pipeline',
        'show_pipeline': True
    })

@login_required
def video_delivered_projects(request):
    """List delivered video projects"""
    ensure_is_video_pm(request.user)
    
    # Get filter form
    filter_form = VideoProjectFilterForm(request.GET or None)
    
    # Get delivered projects
    projects_queryset = VideoProjectService.get_delivered_projects(request.user)
    
    # Apply additional filters if provided
    filters = {}
    if filter_form.is_valid():
        for field_name, value in filter_form.cleaned_data.items():
            if value:
                filters[field_name] = value
    
    if filters:
        # Apply filters to delivered projects
        if filters.get('search'):
            search_term = filters['search']
            projects_queryset = projects_queryset.filter(
                Q(project_name__icontains=search_term) |
                Q(builder_name__icontains=search_term) |
                Q(hs_id__icontains=search_term) |
                Q(opportunity_id__icontains=search_term)
            )
        if filters.get('vendor'):
            projects_queryset = projects_queryset.filter(
                production_vendor__icontains=filters['vendor']
            )
        if filters.get('city'):
            projects_queryset = projects_queryset.filter(city=filters['city'])
        if filters.get('video_product'):
            projects_queryset = projects_queryset.filter(video_product=filters['video_product'])
    
    # Pagination
    paginator = Paginator(projects_queryset, 10)  # 10 projects per page
    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)
    
    # Get filter options for form
    filter_options = VideoProjectService.get_video_filter_options()
    
    return render(request, 'video_production/video_project_list.html', {
        'projects': projects,
        'filter_form': filter_form,
        'filter_options': filter_options,
        'page_title': 'Delivered Video Projects',
        'show_delivered': True
    })

@login_required
def video_submit_cut(request, project_id):
    """Submit video cut for client review"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only submit cuts for your own projects.")
        
        if request.method == 'POST':
            form = VideoCutSubmissionForm(request.POST, project=project)
            if form.is_valid():
                cut = VideoProjectService.submit_video_cut(
                    project_id,
                    form.cleaned_data['cut_number'],
                    request.user
                )
                messages.success(request, f'Cut {cut.cut_number} submitted successfully for project {project.hs_id}')
                return redirect('video_production:project_detail', project_id=project_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = VideoCutSubmissionForm(project=project)
        
        return render(request, 'video_production/video_project_detail.html', {
            'cut_form': form,
            'project': project,
            'page_title': f'Submit Video Cut - {project.hs_id}',
            'show_cut_form': True
        })
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')

@login_required
def video_cut_feedback(request, project_id, cut_number):
    """Provide feedback on video cut"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only provide feedback on your own projects.")
        
        if request.method == 'POST':
            form = VideoCutFeedbackForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['request_rework']:
                    cut = VideoProjectService.request_cut_rework(
                        project_id,
                        cut_number,
                        form.cleaned_data['client_feedback'],
                        request.user
                    )
                    messages.success(request, f'Rework requested for Cut {cut_number}')
                else:
                    messages.success(request, f'Feedback recorded for Cut {cut_number}')
                
                return redirect('video_production:project_detail', project_id=project_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = VideoCutFeedbackForm(initial={'cut_number': cut_number})
        
        return render(request, 'video_production/video_project_detail.html', {
            'feedback_form': form,
            'project': project,
            'cut_number': cut_number,
            'page_title': f'Cut Feedback - {project.hs_id}',
            'show_feedback_form': True
        })
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')

@login_required
def video_submit_voiceover_script(request, project_id):
    """Submit voiceover script for approval"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only submit voiceover scripts for your own projects.")
        
        if request.method == 'POST':
            form = VoiceoverScriptForm(request.POST)
            if form.is_valid():
                script = VideoProjectService.submit_voiceover_script(
                    project_id,
                    form.cleaned_data['script_content'],
                    request.user
                )
                messages.success(request, f'Voiceover script v{script.script_version} submitted for approval')
                return redirect('video_production:project_detail', project_id=project_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = VoiceoverScriptForm()
        
        return render(request, 'video_production/video_project_detail.html', {
            'voiceover_form': form,
            'project': project,
            'page_title': f'Submit Voiceover Script - {project.hs_id}',
            'show_voiceover_form': True
        })
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')

@login_required
def video_approve_voiceover_script(request, project_id, script_version):
    """Approve voiceover script"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only approve voiceover scripts for your own projects.")
        
        script = VideoProjectService.approve_voiceover_script(
            project_id,
            script_version,
            request.user
        )
        
        messages.success(request, f'Voiceover script v{script.script_version} approved successfully')
        return redirect('video_production:project_detail', project_id=project_id)
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')

@login_required
def video_edit_project(request, project_id):
    """Edit existing video project"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only edit your own projects.")
        
        if request.method == 'POST':
            form = VideoProjectEditForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                messages.success(request, f'Project {project.hs_id} updated successfully')
                return redirect('video_production:project_detail', project_id=project_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = VideoProjectEditForm(instance=project)
        
        return render(request, 'video_production/video_project_detail.html', {
            'edit_form': form,
            'project': project,
            'page_title': f'Edit Project - {project.hs_id}',
            'show_edit_form': True
        })
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')

@login_required
def video_complete_project(request, project_id):
    """Mark project as completed and track delivery performance"""
    ensure_is_video_pm(request.user)
    
    try:
        project = VideoProjectService.get_video_project(project_id)
        
        # Check if user owns this project
        if project.video_pm != request.user:
            raise PermissionDenied("You can only complete your own projects.")
        
        delivery = VideoProjectService.track_video_project_delivery(project_id)
        messages.success(request, f'Project {project.hs_id} marked as completed. Delivery performance: {delivery.delivery_performance_rating}')
        
        return redirect('video_production:project_detail', project_id=project_id)
    
    except (VideoProject.DoesNotExist, PermissionDenied) as e:
        messages.error(request, str(e))
        return redirect('video_production:project_list')
