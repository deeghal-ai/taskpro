# projects/views.py
# Add this view function for AJAX updates

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

@login_required
@require_GET
def get_active_timers_json(request):
    """
    AJAX endpoint to fetch active timers data in JSON format.
    Only accessible to management roles (DPM, VIDEO_PM, SENIOR_MANAGER).
    
    Returns:
        JsonResponse: Active timers data and summary
    """
    # Check user authorization
    if not hasattr(request.user, 'role'):
        return JsonResponse({'error': 'User role not defined'}, status=403)
    
    if request.user.role not in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)
    
    try:
        # Get active timers from service
        active_timers = ProjectService.get_all_active_timers()
        summary = ProjectService.get_active_timers_summary()
        
        # Convert to JSON-serializable format
        timers_data = []
        for timer in active_timers:
            timer_json = {
                'id': str(timer['id']),
                'team_member': {
                    'id': timer['team_member']['id'],
                    'username': timer['team_member']['username'],
                    'full_name': timer['team_member']['full_name'],
                    'initials': timer['team_member']['initials']
                },
                'assignment': {
                    'id': str(timer['assignment']['id']),
                    'assignment_id': timer['assignment']['assignment_id'],
                    'sub_task': timer['assignment']['sub_task'],
                    'expected_delivery_date': timer['assignment']['expected_delivery_date'].isoformat() if timer['assignment']['expected_delivery_date'] else None,
                    'projected_formatted': timer['assignment']['projected_formatted']
                },
                'project': {
                    'id': timer['project']['id'],
                    'hs_id': timer['project']['hs_id'],
                    'name': timer['project']['name'],
                    'product': timer['project']['product']
                },
                'task': {
                    'id': timer['task']['id'],
                    'name': timer['task']['name']
                },
                'timer': {
                    'started_at': timer['timer']['started_at'].isoformat(),
                    'started_at_formatted': timer['timer']['started_at_formatted'],
                    'elapsed_seconds': timer['timer']['elapsed_seconds'],
                    'elapsed_formatted': timer['timer']['elapsed_formatted'],
                    'is_long_running': timer['timer']['is_long_running']
                },
                'progress': {
                    'total_worked_formatted': timer['progress']['total_worked_formatted'],
                    'percentage': timer['progress']['percentage'],
                    'status_class': timer['progress']['status_class']
                },
                'urgency': {
                    'status': timer['urgency']['status'],
                    'days_until_deadline': timer['urgency']['days_until_deadline'],
                    'status_class': timer['urgency']['status_class'],
                    'display_text': timer['urgency']['display_text']
                }
            }
            timers_data.append(timer_json)
        
        response_data = {
            'success': True,
            'timers': timers_data,
            'summary': {
                'count': summary['count'],
                'display_text': summary['display_text'],
                'has_timers': summary['has_timers'],
                'team_members': summary.get('team_members', []),
                'more_count': summary.get('more_count', 0)
            },
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception(f"Error in get_active_timers_json: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch active timers',
            'message': str(e) if settings.DEBUG else 'An error occurred'
        }, status=500)


# URL Configuration to add to projects/urls.py
# Add this to your urlpatterns list:
# path('api/active-timers/', views.get_active_timers_json, name='api_active_timers'),