# Active Timers Display - Implementation Plan

## Overview
Add a real-time active timers display in the header (base.html) visible to DPMs, showing all team members currently tracking time with relevant project and task information.

## Data Architecture Analysis

### ActiveTimer Model Structure
```python
ActiveTimer:
├── team_member (OneToOne) → User
│   ├── username
│   ├── first_name
│   └── last_name
├── assignment → TaskAssignment
│   ├── assignment_id
│   ├── task → Task
│   │   ├── project → Project
│   │   │   ├── hs_id
│   │   │   ├── project_name
│   │   │   └── product → Product
│   │   └── product_task → ProductTask
│   │       └── name
│   ├── sub_task (description)
│   ├── expected_delivery_date
│   └── projected_hours
├── started_at (DateTime)
└── last_updated (DateTime)
```

### Key Data Points to Display
1. **Team Member Info**: Name and avatar/initial
2. **Timer Duration**: Live elapsed time since started_at
3. **Project Context**: Project name and HS ID
4. **Task Details**: Task name and sub-task description
5. **Deadline Status**: Expected delivery date and urgency indicator
6. **Progress**: Hours worked vs projected hours

## Implementation Architecture

### Component Structure
```
base.html (header)
├── Active Timers Widget (Collapsible)
│   ├── Summary Badge (count of active timers)
│   ├── Dropdown Panel
│   │   ├── Timer Cards (for each active timer)
│   │   │   ├── Team Member Section
│   │   │   ├── Timer Display
│   │   │   ├── Project/Task Info
│   │   │   └── Progress Bar
│   │   └── Refresh Controls
│   └── Auto-Update Logic (WebSocket/Polling)
```

## Step-by-Step Implementation

### Step 1: Service Layer - Active Timers Fetching
**File**: `projects/services.py`

Add method `get_all_active_timers()`:
```python
@staticmethod
def get_all_active_timers():
    """
    Get all active timers with optimized queries for header display.
    Returns enriched timer data with calculated fields.
    """
    # Single query with all necessary relationships
    active_timers = ActiveTimer.objects.select_related(
        'team_member',
        'assignment__task__project__product',
        'assignment__task__product_task',
        'assignment__assigned_to'
    ).prefetch_related(
        'assignment__daily_totals'
    ).order_by('started_at')
    
    # Enrich with calculated fields
    for timer in active_timers:
        # Calculate elapsed time
        # Calculate total worked hours
        # Determine urgency status
        # Add progress percentage
    
    return active_timers
```

### Step 2: Context Processor for Global Access
**File**: `projects/context_processors.py` (new file)

```python
def active_timers_context(request):
    """
    Make active timers available globally for DPMs.
    """
    if request.user.is_authenticated and request.user.role in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']:
        timers = ProjectService.get_all_active_timers()
        return {
            'global_active_timers': timers,
            'active_timers_count': len(timers)
        }
    return {}
```

### Step 3: Settings Configuration
**File**: `settings.py`

Add context processor:
```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... existing processors
                'projects.context_processors.active_timers_context',
            ],
        },
    },
]
```

### Step 4: Header Template Component
**File**: `templates/partials/active_timers_widget.html` (new file)

Create reusable widget component with:
- Collapsible panel design
- Timer cards with all relevant info
- Real-time timer updates
- Visual indicators for urgency

### Step 5: Update Base Template
**File**: `templates/base.html`

Insert widget in navbar:
```html
<!-- After navbar brand, before nav items -->
{% if user.role in 'DPM,VIDEO_PM,SENIOR_MANAGER' %}
    {% include 'partials/active_timers_widget.html' %}
{% endif %}
```

### Step 6: AJAX Endpoint for Updates
**File**: `projects/views.py`

Add view for fetching timer updates:
```python
@login_required
def get_active_timers_json(request):
    """
    AJAX endpoint for refreshing active timers.
    """
    if request.user.role not in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    timers = ProjectService.get_all_active_timers_json()
    return JsonResponse({'timers': timers})
```

### Step 7: JavaScript for Real-Time Updates
**File**: `static/js/active_timers.js` (new file)

Implement:
- Timer tick updates (every second)
- Data refresh (every 30 seconds)
- Smooth animations
- Sound notifications (optional)

## Data Display Specification

### Timer Card Layout
```
┌─────────────────────────────────────┐
│ [Avatar] John Doe          02:34:15 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 📁 HS2024_001 - Sunset Villa        │
│ 📋 Interior Rendering - Living Room  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 📅 Due: Tomorrow (1 day)     ⚠️     │
│ Progress: ████████░░ 80% (4/5 hrs)  │
└─────────────────────────────────────┘
```

### Information Hierarchy
1. **Primary**: Team member name + Live timer
2. **Secondary**: Project and task names
3. **Tertiary**: Deadline and progress
4. **Visual**: Color coding for urgency

### Status Indicators
- 🟢 Green: On track (< 50% time, < 50% deadline)
- 🟡 Yellow: Attention (> 70% time or approaching deadline)
- 🔴 Red: Overdue or exceeded projected hours
- ⚡ Lightning: Started today
- 🔥 Fire: Running > 4 hours continuously

## Performance Optimization

### Query Strategy
```python
# Single optimized query with all relationships
ActiveTimer.objects.select_related(
    'team_member',
    'assignment__task__project__product',
    'assignment__task__product_task'
).prefetch_related(
    Prefetch(
        'assignment__daily_totals',
        queryset=DailyTimeTotal.objects.filter(
            date_worked=timezone.now().date()
        )
    )
)
```

### Caching Strategy
- Cache timer data for 5 seconds
- Use Redis for WebSocket implementation (future)
- Browser localStorage for user preferences

### Update Frequency
- Timer display: Every 1 second (client-side)
- Data refresh: Every 30 seconds (AJAX)
- Full reload: On timer start/stop events

## UI/UX Design

### Visual Design
```css
/* Floating badge style */
.active-timers-badge {
    position: relative;
    background: #28a745;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 1rem;
    animation: pulse 2s infinite;
}

/* Dropdown panel */
.active-timers-panel {
    position: absolute;
    top: 100%;
    right: 0;
    width: 400px;
    max-height: 500px;
    overflow-y: auto;
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
}
```

### Interaction Patterns
1. **Click badge**: Toggle panel visibility
2. **Hover timer**: Show additional details
3. **Click timer**: Navigate to assignment details
4. **Auto-hide**: Close panel when clicking outside
5. **Notifications**: Badge pulse when new timer starts

## Error Handling

### Edge Cases
1. **No active timers**: Show encouraging message
2. **Network failure**: Show cached data with indicator
3. **Timer > 8 hours**: Show warning indicator
4. **Multiple timers same person**: Data integrity check
5. **Stale timers**: Auto-cleanup after 24 hours

### Fallback Strategies
```javascript
// Graceful degradation
if (!window.WebSocket) {
    // Fall back to polling
    setInterval(refreshTimers, 30000);
}

// Handle network errors
fetch('/api/active-timers/')
    .catch(error => {
        console.error('Failed to fetch timers:', error);
        showOfflineIndicator();
    });
```

## Testing Requirements

### Unit Tests
- Service method returns correct data
- Context processor filters by role
- AJAX endpoint authorization
- Timer calculation accuracy

### Integration Tests
- Full flow from timer start to display
- Multiple concurrent timers
- Role-based visibility
- Performance with 30+ timers

### UI Tests
- Timer updates every second
- Panel open/close behavior
- Responsive design on mobile
- Cross-browser compatibility

## Deployment Checklist

### Pre-Deployment
- [ ] Run migrations if needed
- [ ] Test with production data volume
- [ ] Verify performance metrics
- [ ] Check mobile responsiveness
- [ ] Test all user roles

### Deployment Steps
1. Deploy context processor
2. Deploy service methods
3. Deploy template changes
4. Deploy static files
5. Clear cache
6. Monitor for errors

### Post-Deployment
- [ ] Verify timers display correctly
- [ ] Check performance metrics
- [ ] Monitor error logs
- [ ] Gather user feedback
- [ ] Document any issues

## Future Enhancements

### Phase 2 Features
1. **WebSocket Integration**: Real-time updates without polling
2. **Timer Controls**: Stop/pause timers from header
3. **Notifications**: Desktop notifications for milestones
4. **Analytics**: Timer patterns and productivity insights
5. **Filtering**: Show/hide by project or team member
6. **Export**: Download active timer report
7. **Mobile App**: Native mobile timer display

### Technical Improvements
- Redis caching for timer data
- GraphQL for efficient data fetching
- Service Worker for offline support
- WebRTC for peer-to-peer updates

## Configuration Options

### Settings to Add
```python
# Active Timer Display Settings
ACTIVE_TIMERS_REFRESH_INTERVAL = 30  # seconds
ACTIVE_TIMERS_SHOW_AVATARS = True
ACTIVE_TIMERS_SOUND_NOTIFICATIONS = False
ACTIVE_TIMERS_MAX_DISPLAY = 10
ACTIVE_TIMERS_AUTO_HIDE_PANEL = True
```

## Success Metrics

### Performance KPIs
- Page load impact: < 50ms
- Update latency: < 100ms
- Memory usage: < 5MB
- CPU usage: < 5%

### User Engagement
- Feature adoption rate
- Average views per day
- Click-through to assignments
- User feedback score

## Risk Mitigation

### Potential Issues
1. **Performance degradation**: Implement pagination
2. **Browser compatibility**: Provide polyfills
3. **Network congestion**: Implement throttling
4. **Data inconsistency**: Add integrity checks
5. **User distraction**: Make it dismissible

## Documentation Requirements

### User Documentation
- How to view active timers
- Understanding status indicators
- Interpreting progress bars
- Troubleshooting guide

### Developer Documentation
- API endpoints
- Data structures
- Component architecture
- Extension points