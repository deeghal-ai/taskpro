# projects/management/commands/sync_delivery_ratings.py
from django.core.management.base import BaseCommand
from projects.models import Project, ProjectDelivery
from projects.services import ReportingService

class Command(BaseCommand):
    help = 'Sync delivery performance ratings from projects to delivery records'
    
    def handle(self, *args, **options):
        # Get all projects with deliveries
        projects_with_deliveries = Project.objects.filter(
            deliveries__isnull=False
        ).distinct()
        
        updated_count = 0
        recalculated_dates = set()
        
        for project in projects_with_deliveries:
            if project.delivery_performance_rating:
                # Update all delivery records for this project
                deliveries_to_update = ProjectDelivery.objects.filter(
                    project=project
                ).exclude(
                    delivery_performance_rating=project.delivery_performance_rating
                )
                
                # Store the delivery info before updating
                for delivery in deliveries_to_update:
                    self.stdout.write(
                        f"Updating delivery for project {project.hs_id}: "
                        f"{delivery.delivery_performance_rating} -> {project.delivery_performance_rating}"
                    )
                    recalculated_dates.add((delivery.project_incharge, delivery.delivery_date))
                
                # Perform the update
                updated = deliveries_to_update.update(
                    delivery_performance_rating=project.delivery_performance_rating
                )
                
                if updated > 0:
                    updated_count += updated
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated {updated} delivery records for project {project.hs_id} "
                            f"('{project.project_name}') to rating {project.delivery_performance_rating}"
                        )
                    )
        
        # Recalculate metrics for all affected dates
        self.stdout.write("\nRecalculating metrics...")
        for incharge, date in recalculated_dates:
            ReportingService.calculate_team_member_metrics(incharge, date)
            self.stdout.write(f"✓ Recalculated metrics for {incharge.username} on {date}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted! Total delivery records updated: {updated_count}"
            )
        )