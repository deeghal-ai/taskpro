# Template: projects\templates\projects\reports\base_report.html

## Purpose
Base template for inheritance

## Template Inheritance
- **Extends:** base.html
- **Blocks:** report_scripts, report_content, content, extra_js, extra_css

## Dependencies
- **Includes:** None
- **URLs Used:** None

## Context Variables Required
```python
context = {
    'end_date': ...,  # Required
    'start_date': ...,  # Required
}}
```

## Forms
- **GET to current_url**
  - Fields: start_date, end_date

## JavaScript Functions
No JavaScript functions defined.

## Custom CSS Classes
- Custom: chart-container, date-filter, metric-card, metric-label, metric-value
