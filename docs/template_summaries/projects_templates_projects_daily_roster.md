# Template: projects\templates\projects\daily_roster.html

## Purpose
Roster/schedule display

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:team_member_dashboard, projects:daily_roster, projects:assignment_timesheet, projects:assignment_timesheet, projects:assignment_timesheet, projects:team_member_dashboard, projects:team_member_dashboard

## Context Variables Required
```python
context = {
    'daily_total': ...,  # Required
    'daily_totals': ...,  # Required
    'date_range': ...,  # Required
    'day_group': ...,  # Required
    'filter_form': ...,  # Required
    'title': ...,  # Required
    'total_formatted': ...,  # Required
}}
```

## Forms
- **GET to current_url**
  - Fields: filter_form.week_view, filter_form.date

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: alert-info, assignment-row, badge, bg-info, bg-success, btn, btn-group, btn-loading, card, card-body ... and 13 more
