# Template: projects\templates\projects\task_detail.html

## Purpose
Detail view for displaying single item

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:project_management, projects:create_task_assignment, projects:update_task_assignment, projects:update_quality_rating, projects:create_task_assignment, projects:update_task_assignment, projects:update_quality_rating

## Context Variables Required
```python
context = {
    'active_assignments': ...,  # Required
    'assignment': ...,  # Required
    'assignment_form': ...,  # Required
    'completed_assignments': ...,  # Required
    'project': ...,  # Required
    'task': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to projects:create_task_assignment**
  - Fields: assignment_form.projected_hours, assignment_form.expected_delivery_date, assignment_form.rework_type, assignment_form.assigned_to, assignment_form.sub_task
- **POST to projects:update_task_assignment**
  - Fields: projected_hours, expected_delivery_date, is_active
- **POST to projects:update_quality_rating**
  - Fields: quality_rating

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: assignment-card, assignment-details, assignment-header, badge, btn, btn-group, btn-loading, btn-outline-primary, btn-primary, btn-sm ... and 25 more
