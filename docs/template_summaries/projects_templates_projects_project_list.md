# Template: projects\templates\projects\project_list.html

## Purpose
List/index view for displaying multiple items

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, extra_css, extra_js, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:create_project, projects:project_list, projects:project_detail, projects:project_management, projects:api_cities

## Context Variables Required
```python
context = {
    'city': ...,  # Required
    'dpm': ...,  # Required
    'filter_form': ...,  # Required
    'filters_applied': ...,  # Required
    'key': ...,  # Required
    'num': ...,  # Required
    'product': ...,  # Required
    'project': ...,  # Required
    'projects': ...,  # Required
    'region': ...,  # Required
    'status': ...,  # Required
    'title': ...,  # Required
    'value': ...,  # Required
}}
```

## Forms
- **GET to current_url**
  - Fields: filter_form.status, filter_form.search, filter_form.product, filter_form.dpm, filter_form.region...

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: active-filters, badge, btn, btn-action, btn-loading, btn-primary, card-header, empty-state, filter-body, filter-card ... and 11 more
