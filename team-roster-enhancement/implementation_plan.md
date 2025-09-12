# Team Roster Enhancement Implementation Plan

## Overview
Transform the `/projects/team-roster/` page from simple summary cards to detailed member cards with previous day activity snapshots.

## Data Architecture Understanding

### Current Models & Relationships
- **User** (team_member) → **DailyRoster** (daily attendance status)
- **User** → **TaskAssignment** (assigned tasks) → **DailyTimeTotal** (daily work on tasks)
- **User** → **TimeSession** (individual work sessions with descriptions)
- **User** → **MiscHours** (non-task activities like meetings, training)
- **TaskAssignment** → **Task** → **Project** (project hierarchy)

### Key Data Points Available
1. **Previous Day Status**: Present/Leave/Week Off from DailyRoster
2. **Task Work**: DailyTimeTotal entries showing time per assignment
3. **Task Details**: Project name, task name, hours worked
4. **Misc Activities**: Individual MiscHours entries with activity names and durations
5. **Total Time**: Combined task + misc hours

## Implementation Steps

### Step 1: Service Layer Enhancement
**File**: `projects/services.py`

Add new method `get_team_member_previous_day_snapshot()`:
- Fetches previous working day data (skip weekends/holidays)
- Returns structured data for each team member:
  - Daily status (present/leave/weekoff)
  - Task assignments worked with project names and hours
  - Misc hours entries with activity types
  - Total hours breakdown
  - Efficiency metrics

### Step 2: View Layer Update
**File**: `projects/views.py`

Modify `team_roster_list()` view:
- Call new service method for each team member
- Add previous day snapshot data to context
- Handle edge cases (new employees, no previous data)

### Step 3: Template Redesign
**File**: `projects/templates/projects/team_roster_list.html`

Transform cards to show:
- **Header**: Name, username, current status indicator
- **Previous Day Summary**: Date, status, total hours
- **Task Breakdown**: List of tasks worked with project names and hours
- **Misc Activities**: List of misc activities with durations
- **Visual Indicators**: Progress bars, status badges, hour pills
- **Quick Actions**: View full roster, daily details links

### Step 4: Styling Enhancements
Add CSS for:
- Card hover effects and shadows
- Status color coding (present=green, leave=red, etc.)
- Compact task lists with truncation
- Hour badges and progress bars
- Responsive grid layout

## Data Structure for Template

```python
team_member_data = {
    'member': User object,
    'summary': {  # Current month summary
        'present_days': 22,
        'leave_days': 0,
        'task_hours': '63:31',
        'misc_hours': '01:40',
        'total_hours': '65:11'
    },
    'previous_day': {
        'date': date(2025, 9, 11),
        'status': 'PRESENT',
        'total_minutes': 485,
        'total_formatted': '08:05',
        'task_minutes': 425,
        'misc_minutes': 60,
        'tasks': [
            {
                'assignment_id': 'ASID_000123',
                'task_name': 'Interior Rendering',
                'project_name': 'Sunset Villa',
                'project_hs_id': 'HS2024_001',
                'minutes_worked': 240,
                'formatted_time': '04:00'
            },
            {
                'assignment_id': 'ASID_000124',
                'task_name': 'Exterior View',
                'project_name': 'Urban Tower',
                'project_hs_id': 'HS2024_002',
                'minutes_worked': 185,
                'formatted_time': '03:05'
            }
        ],
        'misc_activities': [
            {
                'activity': 'Team Meeting',
                'activity_type': 'TEAM_ACTIVITY',
                'duration_minutes': 60,
                'formatted_time': '01:00'
            }
        ]
    }
}
```

## Performance Considerations

### Optimization Strategy
1. **Use Bulk Queries**: Single query for all team members' previous day data
2. **Select Related**: Prefetch task→project relationships
3. **Aggregate in DB**: Use Django ORM aggregation for totals
4. **Cache Results**: Consider caching previous day data (5-minute TTL)

### Query Optimization
```python
# Bulk fetch with select_related
DailyTimeTotal.objects.filter(
    team_member__in=team_members,
    date_worked=previous_date
).select_related(
    'assignment__task__project',
    'assignment__task__product_task',
    'team_member'
).order_by('team_member', 'assignment')
```

## Error Handling

### Edge Cases to Handle
1. **No Previous Day Data**: New employee or first day back
2. **Weekend/Holiday**: Find last working day
3. **All Leave Days**: Show appropriate message
4. **Missing Relationships**: Handle deleted projects/tasks gracefully

## Testing Requirements

### Unit Tests
- Service method with various data scenarios
- Edge case handling (no data, all leave, etc.)
- Performance with 50+ team members

### Integration Tests
- Full page load with real data
- Click-through to detailed views
- Responsive layout on mobile/tablet

## Migration Path

### Backward Compatibility
- Keep existing monthly summary data
- Add previous day as enhancement
- Ensure no breaking changes to existing URLs/views

### Feature Flag Option
Consider adding setting to toggle between old/new view:
```python
TEAM_ROSTER_SHOW_DAILY_SNAPSHOT = True
```

## Future Enhancements

### Phase 2 Ideas
1. **Weekly Trends**: Show 7-day activity sparklines
2. **Team Comparison**: Highlight top performers
3. **Filter/Search**: Filter by project, status, or hours
4. **Export Options**: CSV download of team activity
5. **Real-time Updates**: WebSocket for live timer updates
6. **Predictive Analytics**: Flag unusual patterns

## Rollback Plan

If issues arise:
1. Keep original template as `team_roster_list_legacy.html`
2. Add feature flag in settings
3. Monitor performance metrics
4. Quick revert via environment variable

## Success Metrics

Track after deployment:
- Page load time (target: <2 seconds)
- User engagement (clicks to detail views)
- Manager feedback on usefulness
- Database query count (target: <10 queries)