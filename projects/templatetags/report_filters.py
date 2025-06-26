# Create projects/templatetags/__init__.py (empty file)
# Create projects/templatetags/report_filters.py

from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    
@register.filter
def abs(value):
    """Return absolute value."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """
    Returns the value of a dictionary for a given key.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def add_days(value, days):
    """Add days to a date."""
    try:
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value

@register.filter
def dict_get(dictionary, key):
    """
    Template filter to get value from dictionary by key.
    Usage: {{ dictionary|dict_get:key }}
    """
    return dictionary.get(key, [])

@register.simple_tag
def get_all_dates_with_time(daily_totals, misc_hours_entries):
    """
    Get all unique dates that have either assignments or misc hours.
    Returns sorted list of dates.
    """
    all_dates = set()
    
    # Add dates from assignments
    for daily_total in daily_totals:
        all_dates.add(daily_total.date_worked)
    
    # Add dates from misc hours
    for misc_entry in misc_hours_entries:
        all_dates.add(misc_entry.date)
    
    # Return sorted list of dates
    return sorted(all_dates)