# Template: projects\templates\projects\status_update.html

## Purpose
Update/edit existing item form

## Template Inheritance
- **Extends:** base.html
- **Blocks:** content, title

## Dependencies
- **Includes:** None
- **URLs Used:** projects:project_detail

## Context Variables Required
```python
context = {
    'field': ...,  # Required
    'project': ...,  # Required
    'title': ...,  # Required
}}
```

## Forms
- **POST to current_url**

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
