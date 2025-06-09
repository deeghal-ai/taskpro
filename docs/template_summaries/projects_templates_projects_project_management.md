# Template: projects\templates\projects\project_management.html

## Purpose
Form submission page

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:dpm_task_dashboard, projects:project_detail, projects:update_project_configuration, projects:create_project_task, projects:task_detail, projects:update_project_configuration, projects:create_project_task

## Context Variables Required
```python
context = {
    'project': ...,  # Required
    'project_form': ...,  # Required
    'task': ...,  # Required
    'task_form': ...,  # Required
    'tasks': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to projects:update_project_configuration**
  - Fields: project_form.expected_completion_date, project_form.project_incharge, project_form.delivery_performance_rating
- **POST to projects:create_project_task**
  - Fields: task_form.task_type, task_form.estimated_time, task_form.product_task

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: badge, btn, btn-loading, btn-primary, btn-success, card-header, config-section, config-warning, empty-state, empty-state-icon ... and 16 more
