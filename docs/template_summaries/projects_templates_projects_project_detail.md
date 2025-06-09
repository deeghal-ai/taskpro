# Template: projects\templates\projects\project_detail.html

## Purpose
Detail view for displaying single item

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:project_list, projects:project_management, projects:update_project_status, projects:update_project_status, projects:update_project_status

## Context Variables Required
```python
context = {
    'field': ...,  # Required
    'history': ...,  # Required
    'project': ...,  # Required
    'status': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to projects:update_project_status**
  - Fields: status, comments

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: action-card, badge, bg-primary, btn, btn-loading, card-header, data-list, empty-state, history-date, history-table ... and 9 more

## AJAX Endpoints
- {% url  (fetch)
