# Update projects/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import ProjectStatusHistory, TaskAssignment, Project
from .services import ReportingService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ProjectStatusHistory)
def track_status_changes(sender, instance, created, **kwargs):
    """
    Track when a project status changes, handling both Final Delivery 
    and return to pipeline status.
    """
    if not created:
        return
    
    status_name = instance.status.name.lower()
    
    # Check if this is a "Final Delivery" status
    if 'final' in status_name and 'delivery' in status_name:
        try:
            # Track the delivery
            ReportingService.track_project_delivery(
                instance.project,
                instance.changed_at.date()
            )
            logger.info(f"Tracked final delivery for project {instance.project.hs_id}")
            
            # Log the transition
            logger.info(f"Project {instance.project.hs_id} moved to DELIVERED state")
        except Exception as e:
            logger.exception(f"Error tracking delivery: {str(e)}")
    
    # Check if this is "Approval after deemed consumed" - returns to pipeline
    elif 'approval' in status_name and 'deemed' in status_name and 'consumed' in status_name:
        try:
            # Log the transition back to pipeline
            logger.info(f"Project {instance.project.hs_id} moved back to PIPELINE state")
            
            # You might want to remove or update delivery records here
            # depending on your business logic
        except Exception as e:
            logger.exception(f"Error handling pipeline return: {str(e)}")

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

@receiver(pre_save, sender=Project)
def log_project_state_transition(sender, instance, **kwargs):
    """
    Log when a project transitions between pipeline and delivered states.
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