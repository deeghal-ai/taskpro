# projects/services.py
# Add this method to the ProjectService class

@staticmethod
def get_all_active_timers():
    """
    Get all active timers with complete information for header display.
    Optimized for performance with single query and calculated fields.
    
    Returns:
        list: List of enriched active timer objects
    """
    from django.db.models import Sum, Prefetch
    from .models import ActiveTimer, DailyTimeTotal
    import math
    
    try:
        # Fetch all active timers with related data in a single query
        active_timers = ActiveTimer.objects.select_related(
            'team_member',
            'assignment__task__project__product',
            'assignment__task__product_task',
            'assignment__assigned_by'
        ).prefetch_related(
            Prefetch(
                'assignment__daily_totals',
                queryset=DailyTimeTotal.objects.all(),
                to_attr='all_daily_totals'
            )
        ).order_by('started_at')
        
        enriched_timers = []
        current_time = timezone.now()
        today = timezone.localtime(current_time).date()
        
        for timer in active_timers:
            # Calculate elapsed time
            elapsed_seconds = (current_time - timer.started_at).total_seconds()
            elapsed_minutes = int(elapsed_seconds // 60)
            hours = elapsed_minutes // 60
            minutes = elapsed_minutes % 60
            seconds = int(elapsed_seconds % 60)
            
            # Format elapsed time
            elapsed_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Calculate total worked minutes for this assignment
            total_worked_minutes = sum(
                dt.total_minutes for dt in timer.assignment.all_daily_totals
            )
            
            # Add today's current session (approximate)
            total_worked_minutes += elapsed_minutes
            
            # Get projected hours
            projected_minutes = timer.assignment.projected_hours or 0
            
            # Calculate progress percentage
            if projected_minutes > 0:
                progress_percentage = min(100, (total_worked_minutes / projected_minutes) * 100)
            else:
                progress_percentage = 0
            
            # Calculate deadline urgency
            urgency_status = 'normal'
            days_until_deadline = None
            
            if timer.assignment.expected_delivery_date:
                days_until_deadline = (timer.assignment.expected_delivery_date - today).days
                
                if days_until_deadline < 0:
                    urgency_status = 'overdue'
                elif days_until_deadline == 0:
                    urgency_status = 'today'
                elif days_until_deadline == 1:
                    urgency_status = 'tomorrow'
                elif days_until_deadline <= 3:
                    urgency_status = 'soon'
            
            # Determine if timer is running long
            is_long_running = elapsed_minutes > 240  # More than 4 hours
            
            # Get task and project info
            task = timer.assignment.task
            project = task.project
            product_task = task.product_task
            
            # Build enriched timer object
            enriched_timer = {
                'id': timer.id,
                'team_member': {
                    'id': timer.team_member.id,
                    'username': timer.team_member.username,
                    'full_name': timer.team_member.get_full_name() or timer.team_member.username,
                    'first_name': timer.team_member.first_name,
                    'last_name': timer.team_member.last_name,
                    'initials': ProjectService._get_user_initials(timer.team_member)
                },
                'assignment': {
                    'id': timer.assignment.id,
                    'assignment_id': timer.assignment.assignment_id,
                    'sub_task': timer.assignment.sub_task or 'No description',
                    'expected_delivery_date': timer.assignment.expected_delivery_date,
                    'projected_hours': timer.assignment.projected_hours,
                    'projected_formatted': ProjectService._format_minutes(projected_minutes)
                },
                'project': {
                    'id': project.id,
                    'hs_id': project.hs_id,
                    'name': project.project_name,
                    'product': project.product.name if project.product else 'Unknown'
                },
                'task': {
                    'id': task.id,
                    'name': product_task.name if product_task else task.custom_task_name or 'Unknown Task'
                },
                'timer': {
                    'started_at': timer.started_at,
                    'started_at_formatted': timer.started_at.strftime('%I:%M %p'),
                    'elapsed_seconds': int(elapsed_seconds),
                    'elapsed_minutes': elapsed_minutes,
                    'elapsed_formatted': elapsed_formatted,
                    'is_long_running': is_long_running
                },
                'progress': {
                    'total_worked_minutes': total_worked_minutes,
                    'total_worked_formatted': ProjectService._format_minutes(total_worked_minutes),
                    'percentage': round(progress_percentage, 1),
                    'status_class': ProjectService._get_progress_status_class(progress_percentage)
                },
                'urgency': {
                    'status': urgency_status,
                    'days_until_deadline': days_until_deadline,
                    'status_class': ProjectService._get_urgency_status_class(urgency_status),
                    'display_text': ProjectService._get_deadline_display_text(days_until_deadline)
                }
            }
            
            enriched_timers.append(enriched_timer)
        
        return enriched_timers
        
    except Exception as e:
        logger.exception(f"Error fetching active timers: {str(e)}")
        return []

@staticmethod
def _get_user_initials(user):
    """Get user initials for avatar display."""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[:2].upper()
    else:
        return user.username[:2].upper()

@staticmethod
def _get_progress_status_class(percentage):
    """Determine CSS class based on progress percentage."""
    if percentage >= 100:
        return 'progress-exceeded'
    elif percentage >= 80:
        return 'progress-high'
    elif percentage >= 60:
        return 'progress-medium'
    else:
        return 'progress-low'

@staticmethod
def _get_urgency_status_class(status):
    """Determine CSS class based on urgency status."""
    status_classes = {
        'overdue': 'urgency-overdue',
        'today': 'urgency-today',
        'tomorrow': 'urgency-tomorrow',
        'soon': 'urgency-soon',
        'normal': 'urgency-normal'
    }
    return status_classes.get(status, 'urgency-normal')

@staticmethod
def _get_deadline_display_text(days):
    """Get human-readable deadline text."""
    if days is None:
        return 'No deadline'
    elif days < 0:
        return f'Overdue by {abs(days)} day{"s" if abs(days) != 1 else ""}'
    elif days == 0:
        return 'Due today'
    elif days == 1:
        return 'Due tomorrow'
    else:
        return f'Due in {days} days'

@staticmethod
def get_active_timers_summary():
    """
    Get a summary of active timers for badge display.
    
    Returns:
        dict: Summary with count and basic info
    """
    try:
        count = ActiveTimer.objects.count()
        
        if count == 0:
            return {
                'count': 0,
                'display_text': 'No active timers',
                'has_timers': False
            }
        
        # Get team member names for tooltip
        timers = ActiveTimer.objects.select_related('team_member')[:5]
        team_members = [t.team_member.get_full_name() or t.team_member.username for t in timers]
        
        more_count = max(0, count - 5)
        
        return {
            'count': count,
            'display_text': f'{count} active timer{"s" if count != 1 else ""}',
            'has_timers': True,
            'team_members': team_members,
            'more_count': more_count
        }
        
    except Exception as e:
        logger.exception(f"Error getting timer summary: {str(e)}")
        return {
            'count': 0,
            'display_text': 'Error loading timers',
            'has_timers': False
        }