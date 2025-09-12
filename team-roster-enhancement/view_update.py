# projects/views.py
# Replace the existing team_roster_list function with this enhanced version

@login_required
def team_roster_list(request):
    """
    Display list of all team members with enhanced cards showing previous day snapshots.
    """
    # Check if user has management access (DPM, VIDEO_PM, or SENIOR_MANAGER)
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
    # Get all team members (excluding DPMs)
    team_members = User.objects.filter(role='TEAM_MEMBER').order_by('first_name', 'last_name')
    
    # Get current month and date info
    today = date.today()
    
    # Get previous day snapshots for all team members (optimized bulk query)
    previous_day_snapshots = ProjectService.get_bulk_previous_day_snapshots(team_members, today)
    
    # Build team member data with both monthly summary and previous day snapshot
    team_member_data = []
    
    for member in team_members:
        # Get monthly summary (optimized version)
        success, summary = ProjectService.get_monthly_roster_summary_only(member, today.year, today.month)
        
        if not success:
            summary = {
                'present_days': 0,
                'leave_days': 0,
                'weekoff_days': 0,
                'task_hours': '00:00',
                'misc_hours': '00:00',
                'total_hours': '00:00'
            }
        
        # Get previous day snapshot
        previous_day = previous_day_snapshots.get(member.id, {
            'date': today - timedelta(days=1),
            'status': 'NO_DATA',
            'status_display': 'No Data',
            'total_minutes': 0,
            'total_formatted': '00:00',
            'task_minutes': 0,
            'misc_minutes': 0,
            'tasks': [],
            'misc_activities': [],
            'has_data': False
        })
        
        # Calculate efficiency percentage for previous day
        if previous_day['total_minutes'] > 0:
            # Assuming 8 hours (480 minutes) as standard working day
            efficiency_percentage = min(100, (previous_day['total_minutes'] / 480) * 100)
        else:
            efficiency_percentage = 0
        
        previous_day['efficiency_percentage'] = round(efficiency_percentage, 1)
        
        # Determine card status color
        if previous_day['status'] == 'PRESENT':
            if previous_day['total_minutes'] >= 420:  # 7+ hours
                card_status_class = 'status-excellent'
            elif previous_day['total_minutes'] >= 360:  # 6+ hours
                card_status_class = 'status-good'
            elif previous_day['total_minutes'] >= 240:  # 4+ hours
                card_status_class = 'status-fair'
            else:
                card_status_class = 'status-low'
        elif previous_day['status'] in ['LEAVE', 'SICK_LEAVE']:
            card_status_class = 'status-leave'
        elif previous_day['status'] == 'WEEK_OFF':
            card_status_class = 'status-weekoff'
        elif previous_day['status'] == 'HOLIDAY':
            card_status_class = 'status-holiday'
        else:
            card_status_class = 'status-nodata'
        
        previous_day['card_status_class'] = card_status_class
        
        team_member_data.append({
            'member': member,
            'summary': summary,
            'previous_day': previous_day
        })
    
    # Sort team members by previous day total hours (most productive first)
    team_member_data.sort(key=lambda x: x['previous_day']['total_minutes'], reverse=True)
    
    context = {
        'team_members': team_member_data,
        'current_month': today.strftime('%B %Y'),
        'previous_date': previous_day_snapshots[team_members[0].id]['date'] if team_members and team_members[0].id in previous_day_snapshots else today - timedelta(days=1),
        'title': 'Team Roster',
        'show_previous_day': True  # Feature flag for easy rollback
    }
    
    return render(request, 'projects/team_roster_list.html', context)