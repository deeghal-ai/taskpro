# projects/services.py
# Add this method to the ProjectService class

@staticmethod
def get_team_member_previous_day_snapshot(team_member, reference_date=None):
    """
    Get previous working day snapshot for a team member.
    
    Args:
        team_member: User object of the team member
        reference_date: Date to look back from (default: today)
        
    Returns:
        dict: Previous day activity snapshot
    """
    from django.db.models import Sum, Prefetch
    from .models import DailyRoster, DailyTimeTotal, MiscHours, Holiday
    
    try:
        # Use reference date or today
        if reference_date is None:
            reference_date = timezone.localtime(timezone.now()).date()
        
        # Find the previous working day (skip weekends and holidays)
        previous_date = reference_date - timedelta(days=1)
        attempts = 0
        max_attempts = 7  # Look back max 7 days
        
        while attempts < max_attempts:
            # Check if it's a weekend
            if previous_date.weekday() in [5, 6]:  # Saturday, Sunday
                previous_date -= timedelta(days=1)
                attempts += 1
                continue
            
            # Check if it's a holiday
            is_holiday = Holiday.objects.filter(
                date=previous_date,
                location='Gurgaon',
                is_active=True
            ).exists()
            
            if is_holiday:
                previous_date -= timedelta(days=1)
                attempts += 1
                continue
            
            # Valid working day found
            break
        
        # Get roster entry for status
        roster_entry = DailyRoster.objects.filter(
            team_member=team_member,
            date=previous_date
        ).first()
        
        # Default snapshot if no data
        if not roster_entry:
            return {
                'date': previous_date,
                'status': 'NO_DATA',
                'status_display': 'No Data',
                'total_minutes': 0,
                'total_formatted': '00:00',
                'task_minutes': 0,
                'misc_minutes': 0,
                'tasks': [],
                'misc_activities': [],
                'has_data': False
            }
        
        # Get task work for the day
        daily_totals = DailyTimeTotal.objects.filter(
            team_member=team_member,
            date_worked=previous_date
        ).select_related(
            'assignment__task__project',
            'assignment__task__product_task'
        ).order_by('-total_minutes')
        
        # Build task list
        tasks = []
        task_minutes = 0
        
        for dt in daily_totals:
            if dt.total_minutes > 0:
                task_name = dt.assignment.task.product_task.name if dt.assignment.task.product_task else dt.assignment.task.custom_task_name
                project = dt.assignment.task.project
                
                tasks.append({
                    'assignment_id': dt.assignment.assignment_id,
                    'task_name': task_name[:30] + '...' if len(task_name) > 30 else task_name,
                    'project_name': project.project_name[:25] + '...' if len(project.project_name) > 25 else project.project_name,
                    'project_hs_id': project.hs_id,
                    'minutes_worked': dt.total_minutes,
                    'formatted_time': ProjectService._format_minutes(dt.total_minutes),
                    'is_completed': dt.assignment.is_completed
                })
                task_minutes += dt.total_minutes
        
        # Get misc hours for the day
        misc_entries = MiscHours.objects.filter(
            team_member=team_member,
            date=previous_date
        ).order_by('-duration_minutes')
        
        # Build misc activities list
        misc_activities = []
        misc_minutes = 0
        
        for misc in misc_entries:
            misc_activities.append({
                'activity': misc.activity[:30] + '...' if len(misc.activity) > 30 else misc.activity,
                'activity_type': misc.activity_type or 'UNCATEGORIZED',
                'activity_type_display': misc.get_activity_type_display() if misc.activity_type else 'Other',
                'duration_minutes': misc.duration_minutes,
                'formatted_time': misc.get_formatted_duration()
            })
            misc_minutes += misc.duration_minutes
        
        # Also add legacy misc hours if any
        if roster_entry.misc_hours > 0:
            misc_activities.append({
                'activity': roster_entry.misc_description or 'Miscellaneous Work',
                'activity_type': 'LEGACY',
                'activity_type_display': 'Other',
                'duration_minutes': roster_entry.misc_hours,
                'formatted_time': roster_entry.get_misc_hours_formatted()
            })
            misc_minutes += roster_entry.misc_hours
        
        # Calculate totals
        total_minutes = task_minutes + misc_minutes
        
        return {
            'date': previous_date,
            'status': roster_entry.status,
            'status_display': roster_entry.get_status_display(),
            'total_minutes': total_minutes,
            'total_formatted': ProjectService._format_minutes(total_minutes),
            'task_minutes': task_minutes,
            'task_formatted': ProjectService._format_minutes(task_minutes),
            'misc_minutes': misc_minutes,
            'misc_formatted': ProjectService._format_minutes(misc_minutes),
            'tasks': tasks[:5],  # Limit to top 5 tasks
            'more_tasks_count': max(0, len(tasks) - 5),
            'misc_activities': misc_activities[:3],  # Limit to top 3 misc activities
            'more_misc_count': max(0, len(misc_activities) - 3),
            'has_data': total_minutes > 0 or roster_entry.status != 'PRESENT'
        }
        
    except Exception as e:
        logger.exception(f"Error getting previous day snapshot: {str(e)}")
        return {
            'date': reference_date - timedelta(days=1),
            'status': 'ERROR',
            'status_display': 'Error',
            'total_minutes': 0,
            'total_formatted': '00:00',
            'task_minutes': 0,
            'misc_minutes': 0,
            'tasks': [],
            'misc_activities': [],
            'has_data': False
        }


@staticmethod
def get_bulk_previous_day_snapshots(team_members, reference_date=None):
    """
    Optimized method to get previous day snapshots for multiple team members.
    Uses bulk queries to minimize database hits.
    
    Args:
        team_members: QuerySet or list of User objects
        reference_date: Date to look back from (default: today)
        
    Returns:
        dict: Mapping of team_member.id to snapshot data
    """
    from django.db.models import Sum, Prefetch
    from .models import DailyRoster, DailyTimeTotal, MiscHours, Holiday
    
    try:
        # Use reference date or today
        if reference_date is None:
            reference_date = timezone.localtime(timezone.now()).date()
        
        # Find the previous working day
        previous_date = reference_date - timedelta(days=1)
        attempts = 0
        max_attempts = 7
        
        while attempts < max_attempts:
            if previous_date.weekday() in [5, 6]:  # Weekend
                previous_date -= timedelta(days=1)
                attempts += 1
                continue
            
            is_holiday = Holiday.objects.filter(
                date=previous_date,
                location='Gurgaon',
                is_active=True
            ).exists()
            
            if is_holiday:
                previous_date -= timedelta(days=1)
                attempts += 1
                continue
            
            break
        
        # Bulk fetch roster entries
        roster_entries = {
            r.team_member_id: r
            for r in DailyRoster.objects.filter(
                team_member__in=team_members,
                date=previous_date
            )
        }
        
        # Bulk fetch daily totals with related data
        daily_totals = DailyTimeTotal.objects.filter(
            team_member__in=team_members,
            date_worked=previous_date,
            total_minutes__gt=0
        ).select_related(
            'assignment__task__project',
            'assignment__task__product_task',
            'team_member'
        ).order_by('team_member', '-total_minutes')
        
        # Group daily totals by team member
        member_tasks = {}
        for dt in daily_totals:
            if dt.team_member_id not in member_tasks:
                member_tasks[dt.team_member_id] = []
            
            task_name = dt.assignment.task.product_task.name if dt.assignment.task.product_task else dt.assignment.task.custom_task_name
            project = dt.assignment.task.project
            
            member_tasks[dt.team_member_id].append({
                'assignment_id': dt.assignment.assignment_id,
                'task_name': task_name[:30] + '...' if len(task_name) > 30 else task_name,
                'project_name': project.project_name[:25] + '...' if len(project.project_name) > 25 else project.project_name,
                'project_hs_id': project.hs_id,
                'minutes_worked': dt.total_minutes,
                'formatted_time': ProjectService._format_minutes(dt.total_minutes),
                'is_completed': dt.assignment.is_completed
            })
        
        # Bulk fetch misc hours
        misc_entries = MiscHours.objects.filter(
            team_member__in=team_members,
            date=previous_date
        ).order_by('team_member', '-duration_minutes')
        
        # Group misc entries by team member
        member_misc = {}
        for misc in misc_entries:
            if misc.team_member_id not in member_misc:
                member_misc[misc.team_member_id] = []
            
            member_misc[misc.team_member_id].append({
                'activity': misc.activity[:30] + '...' if len(misc.activity) > 30 else misc.activity,
                'activity_type': misc.activity_type or 'UNCATEGORIZED',
                'activity_type_display': misc.get_activity_type_display() if misc.activity_type else 'Other',
                'duration_minutes': misc.duration_minutes,
                'formatted_time': misc.get_formatted_duration()
            })
        
        # Build snapshots for each team member
        snapshots = {}
        for member in team_members:
            roster = roster_entries.get(member.id)
            tasks = member_tasks.get(member.id, [])
            misc_activities = member_misc.get(member.id, [])
            
            # Calculate task minutes
            task_minutes = sum(t['minutes_worked'] for t in tasks)
            
            # Calculate misc minutes
            misc_minutes = sum(m['duration_minutes'] for m in misc_activities)
            
            # Add legacy misc hours if roster exists
            if roster and roster.misc_hours > 0:
                misc_activities.append({
                    'activity': roster.misc_description or 'Miscellaneous Work',
                    'activity_type': 'LEGACY',
                    'activity_type_display': 'Other',
                    'duration_minutes': roster.misc_hours,
                    'formatted_time': roster.get_misc_hours_formatted()
                })
                misc_minutes += roster.misc_hours
            
            total_minutes = task_minutes + misc_minutes
            
            if roster:
                snapshot = {
                    'date': previous_date,
                    'status': roster.status,
                    'status_display': roster.get_status_display(),
                    'total_minutes': total_minutes,
                    'total_formatted': ProjectService._format_minutes(total_minutes),
                    'task_minutes': task_minutes,
                    'task_formatted': ProjectService._format_minutes(task_minutes),
                    'misc_minutes': misc_minutes,
                    'misc_formatted': ProjectService._format_minutes(misc_minutes),
                    'tasks': tasks[:5],
                    'more_tasks_count': max(0, len(tasks) - 5),
                    'misc_activities': misc_activities[:3],
                    'more_misc_count': max(0, len(misc_activities) - 3),
                    'has_data': total_minutes > 0 or roster.status != 'PRESENT'
                }
            else:
                snapshot = {
                    'date': previous_date,
                    'status': 'NO_DATA',
                    'status_display': 'No Data',
                    'total_minutes': 0,
                    'total_formatted': '00:00',
                    'task_minutes': 0,
                    'misc_minutes': 0,
                    'tasks': [],
                    'misc_activities': [],
                    'has_data': False
                }
            
            snapshots[member.id] = snapshot
        
        return snapshots
        
    except Exception as e:
        logger.exception(f"Error getting bulk previous day snapshots: {str(e)}")
        # Return empty snapshots for all members
        return {
            member.id: {
                'date': reference_date - timedelta(days=1),
                'status': 'ERROR',
                'status_display': 'Error',
                'total_minutes': 0,
                'total_formatted': '00:00',
                'task_minutes': 0,
                'misc_minutes': 0,
                'tasks': [],
                'misc_activities': [],
                'has_data': False
            }
            for member in team_members
        }