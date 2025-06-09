# Template: projects\templates\projects\monthly_roster.html

## Purpose
Roster/schedule display

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:team_member_dashboard, projects:roster_date, projects:roster_date, projects:update_roster_day, projects:update_roster_day

## Context Variables Required
```python
context = {
    'day_roster': ...,  # Required
    'misc_hours_form': ...,  # Required
    'monthly_data': ...,  # Required
    'next_month': ...,  # Required
    'prev_month': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to projects:update_roster_day**
  - Fields: notes, date, status
- **POST to current_url**
  - Fields: misc_hours_form.date, misc_hours_form.activity, duration_minutes, add_misc_hours, duration_hours

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: add-misc-btn, alert, bg-success, btn-loading, calendar-card, calendar-legend, card-header, day-cell, day-hours, day-number ... and 25 more
