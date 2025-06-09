# Template: projects\templates\projects\assignment_timesheet.html

## Purpose
Time tracking and timesheet display

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:team_member_dashboard

## Context Variables Required
```python
context = {
    'assignment': ...,  # Required
    'assignment_summary': ...,  # Required
    'daily_total': ...,  # Required
    'daily_totals': ...,  # Required
    'session': ...,  # Required
    'sessions': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to current_url**
  - Fields: duration_minutes, edit_session_duration, duration_hours, session_id

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: alert, badge, bg-primary, btn, btn-loading, btn-sm, card-header, data-card, edited-badge, empty-state ... and 22 more
