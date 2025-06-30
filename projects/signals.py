# Update projects/signals.py - Much simpler without stored metrics!

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import ProjectStatusHistory, TaskAssignment, Project
from .services import ReportingService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ProjectStatusHistory)
def track_status_changes(sender, instance, created, **kwargs):
    """
    Track when a project status changes - simplified version.
    Just track delivery events, no complex metrics calculation.
    """
    if not created:
        return
    
    # Check if this is a "Final Delivery" status using category_two field
    if instance.status.category_two == 'Final Delivery':
        try:
            # Just track the delivery event - no metrics calculation needed!
            ReportingService.track_project_delivery(
                instance.project,
                instance.changed_at.date()
            )
            logger.info(f"Tracked final delivery for project {instance.project.hs_id}")
        except Exception as e:
            logger.exception(f"Error tracking delivery: {str(e)}")


# Removed the complex assignment completion signal - no longer needed!
# Metrics are now calculated on-demand when reports are viewed

@receiver(pre_save, sender=Project)
def log_project_state_transition(sender, instance, **kwargs):
    """
    Simple logging of project state transitions - no metrics calculation.
    """
    if instance.pk:  # Only for existing projects
        try:
            old_project = Project.objects.get(pk=instance.pk)
            
            # Check if status is changing
            if old_project.current_status != instance.current_status:
                old_is_delivered = old_project.is_delivered
                new_is_delivered = instance.is_delivered
                
                if old_is_delivered != new_is_delivered:
                    if new_is_delivered:
                        logger.info(f"Project {instance.hs_id} transitioning from PIPELINE to DELIVERED")
                    else:
                        logger.info(f"Project {instance.hs_id} transitioning from DELIVERED to PIPELINE")
        except Project.DoesNotExist:
            pass