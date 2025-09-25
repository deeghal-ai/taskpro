# Minimal Project Man-Hours Implementation

## Overview
Calculate and display total man-hours on the fly in the project detail page without any model changes.

## Implementation (3 Simple Steps)

### Step 1: Update Project Service
**File**: `projects/services.py` - Add this method to `ProjectService` class

```python
@staticmethod
def calculate_project_total_hours(project_id):
    """
    Calculate total man-hours for a project from DailyTimeTotal.
    Returns decimal hours (e.g., 45.5 for 45 hours 30 minutes).
    """
    from django.db.models import Sum
    from projects.models import TaskAssignment
    
    try:
        # Single query to get total minutes across all assignments
        total_minutes = TaskAssignment.objects.filter(
            task__project_id=project_id
        ).aggregate(
            total=Sum('daily_totals__total_minutes')
        )['total'] or 0
        
        # Convert to decimal hours (e.g., 90 minutes = 1.5 hours)
        total_hours = round(total_minutes / 60, 2)
        
        return total_hours
        
    except Exception as e:
        logger.error(f"Error calculating project hours: {str(e)}")
        return 0
```

### Step 2: Update Project Detail View
**File**: `projects/views.py` - Add one line in the `project_detail` function

Find the section where the context is being prepared (near the end of the function), and add:

```python
@login_required
def project_detail(request, project_id):
    # ... existing code ...
    
    # Get status history (existing)
    success, status_history = ProjectService.get_project_status_history(project_id)
    
    # Get deliveries (existing)
    deliveries = ProjectDelivery.objects.filter(project_id=project_id).order_by('-delivery_date')
    
    # NEW: Calculate total man-hours (add this line)
    total_man_hours = ProjectService.calculate_project_total_hours(project_id)
    
    context = {
        'project': project,
        'status_history': status_history,
        'deliveries': deliveries,
        'status_options': status_options,
        'total_man_hours': total_man_hours,  # NEW: Add to context
    }
    
    return render(request, 'projects/project_detail.html', context)
```

### Step 3: Update Project Detail Template
**File**: `projects/templates/projects/project_detail.html`

Add this field in the "Product Information" card (or wherever you prefer):

```html
<!-- Find the Product Information section and add this field -->
<dt>Man Hours</dt>
<dd>
    <strong>{{ total_man_hours }}</strong> hours
</dd>
```

Or if you want it more prominent, add it in the "Important Dates" section:

```html
<!-- In the Important Dates section -->
<dt>Expected TAT</dt>
<dd>{{ project.expected_tat|default:"Not specified" }}</dd>

<!-- NEW: Add after Expected TAT -->
<dt>Man Hours</dt>
<dd>
    <strong>{{ total_man_hours }}</strong> hours
</dd>

<dt>Expected Completion</dt>
<dd>{{ project.expected_completion_date|date:"M d, Y"|default:"Not specified" }}</dd>
```

## That's It!

### What This Does:
- Calculates total worked hours by summing all `DailyTimeTotal.total_minutes` for all assignments in the project
- Converts minutes to decimal hours (e.g., 1 hour 30 minutes = 1.5 hours)
- Displays as a single numerical value on the project detail page
- No database changes required
- No model modifications needed
- Single efficient database query

### Performance Note:
This uses a single aggregated query that's executed only when the project detail page loads. For a project with hundreds of assignments, this will still be very fast as the aggregation happens at the database level.

### Example Display:
- If total worked time is 45 hours and 30 minutes, it will show: **45.5 hours**
- If no time has been tracked yet, it will show: **0 hours**