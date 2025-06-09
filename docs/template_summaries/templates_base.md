# Template: templates\base.html

## Purpose
Base template for inheritance

## Template Inheritance
- **Extends:** None (base template)
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:project_list, projects:dpm_task_dashboard, projects:create_project, projects:team_overview_report, projects:delivery_performance_report, projects:team_member_dashboard, projects:my_report, admin:index, accounts:logout, accounts:logout

## Context Variables Required
```python
context = {
    'message': ...,  # Required
    'user': ...,  # Required
}}
```

## Forms
- **POST to accounts:logout**

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
