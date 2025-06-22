from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project

class Command(BaseCommand):
    help = 'Updates the purchase_date and sales_confirmation_date of existing projects to match their latest status history date.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows which projects would be updated without saving changes.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No changes will be saved ==='))

        self.stdout.write(self.style.SUCCESS('🚀 Starting to update project dates based on latest status...'))
        
        projects_checked = 0
        projects_updated_count = 0
        
        all_projects = Project.objects.prefetch_related('status_history').all()
        total_projects = all_projects.count()

        with transaction.atomic():
            for i, project in enumerate(all_projects):
                projects_checked += 1
                if i > 0 and i % 100 == 0:
                    self.stdout.write(f'  📊 Checked {i}/{total_projects} projects...')

                latest_history = project.status_history.filter(
                    comments='Imported from CSV'
                ).order_by('-changed_at').first()

                if latest_history:
                    latest_date = latest_history.changed_at.date()
                    
                    if project.purchase_date != latest_date:
                        if dry_run:
                            self.stdout.write(self.style.SUCCESS(f"  [DRY RUN] Would update Project {project.hs_id}: Date {project.purchase_date} -> {latest_date}"))
                        else:
                            project.purchase_date = latest_date
                            project.sales_confirmation_date = latest_date
                            project.save(update_fields=['purchase_date', 'sales_confirmation_date'])
                        
                        projects_updated_count += 1
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\nDRY RUN COMPLETE: Found {projects_updated_count} projects whose dates would be updated.'))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated dates for {projects_updated_count} projects.'))
        
        self.stdout.write('🎉 Date update process finished.')