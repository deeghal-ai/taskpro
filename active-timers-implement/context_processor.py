# projects/context_processors.py
# New file to create

from .services import ProjectService

def active_timers_context(request):
    """
    Context processor to make active timers available globally in templates.
    Only available for management roles (DPM, VIDEO_PM, SENIOR_MANAGER).
    
    Args:
        request: HttpRequest object
        
    Returns:
        dict: Context variables for templates
    """
    # Default context
    context = {
        'show_active_timers': False,
        'active_timers': [],
        'active_timers_summary': {
            'count': 0,
            'display_text': '',
            'has_timers': False
        }
    }
    
    # Check if user is authenticated and has management role
    if request.user.is_authenticated:
        user_role = getattr(request.user, 'role', None)
        
        if user_role in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']:
            # Get active timers data
            active_timers = ProjectService.get_all_active_timers()
            summary = ProjectService.get_active_timers_summary()
            
            context.update({
                'show_active_timers': True,
                'active_timers': active_timers,
                'active_timers_summary': summary,
                'is_management_user': True
            })
    
    return context