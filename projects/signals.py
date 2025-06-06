# projects/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProjectStatusHistory, TaskAssignment
from .services import ReportingService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ProjectStatusHistory)
def track_final_delivery(sender, instance, created, **kwargs):
    """
    Automatically track when a project reaches final delivery status.
    """
    if not created:
        return
    
    # Check if this is a "Final Delivery" status
    status_name = instance.status.name.lower()
    if 'final' in status_name and 'delivery' in status_name:
        try:
            ReportingService.track_project_delivery(
                instance.project,
                instance.changed_at.date()
            )
            logger.info(f"Tracked final delivery for project {instance.project.hs_id}")
        except Exception as e:
            logger.exception(f"Error tracking delivery: {str(e)}")

@receiver(post_save, sender=TaskAssignment)
def update_metrics_on_completion(sender, instance, created, **kwargs):
    """
    Update metrics when an assignment is completed.
    """
    if not created and instance.is_completed and instance.completion_date:
        try:
            ReportingService.calculate_team_member_metrics(
                instance.assigned_to,
                instance.completion_date.date()
            )
            logger.info(f"Updated metrics for {instance.assigned_to.username} on assignment completion")
        except Exception as e:
            logger.exception(f"Error updating metrics: {str(e)}")