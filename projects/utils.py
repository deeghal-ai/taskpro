"""
Utility functions for the projects app
"""
from django.utils import timezone
from datetime import datetime, date
import pytz


def make_aware_datetime(dt):
    """
    Convert a naive datetime to timezone-aware datetime.
    If the datetime is already timezone-aware, return it as-is.
    
    Args:
        dt: datetime object or date object
        
    Returns:
        timezone-aware datetime object
    """
    if dt is None:
        return None
    
    # If it's a date object, convert to datetime at start of day
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    # If it's already timezone-aware, return as-is
    if timezone.is_aware(dt):
        return dt
    
    # Make it timezone-aware using the current timezone
    return timezone.make_aware(dt, timezone.get_current_timezone())


def safe_completion_date(dt):
    """
    Safely handle completion date assignment to avoid timezone warnings.
    
    Args:
        dt: datetime object, date object, or None
        
    Returns:
        timezone-aware datetime object or None
    """
    if dt is None:
        return None
    
    return make_aware_datetime(dt) 