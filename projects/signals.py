# projects/signals.py (new file)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProjectStatusHistory
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

# Don't forget to register signals in apps.py
# projects/apps.py
class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"
    
    def ready(self):
        import projects.signals  # noqa