# Template: projects\templates\projects\team_member_dashboard.html

## Purpose
Dashboard view with summary information

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:daily_roster, projects:roster, projects:assignment_timesheet, projects:assignment_timesheet

## Context Variables Required
```python
context = {
    'active_assignments': ...,  # Required
    'active_timer': ...,  # Required
    'assignment': ...,  # Required
    'completed_assignments': ...,  # Required
    'elapsed_time': ...,  # Required
    'now': ...,  # Required
    'timer_stop_form': ...,  # Required
    'title': ...,  # Required
    'today_summary': ...,  # Required
}}
```

## Forms
- **POST to current_url**
  - Fields: start_timer, assignment_id
- **POST to current_url**
  - Fields: mark_completed, assignment_id
- **POST to current_url**
  - Fields: timer_stop_form.description, stop_timer, timer_stop_form.is_completed
- **POST to current_url**
  - Fields: duration_minutes, date, is_completed, assignment_id, description...

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: assignment-card, badge, bg-danger, bg-primary, btn, btn-group, btn-loading, btn-timer-start, btn-timer-stop, due-today ... and 10 more
