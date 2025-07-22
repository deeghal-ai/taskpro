from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project, ProjectStatusHistory

class Command(BaseCommand):
    help = 'Clean up duplicate Sales Confirmation histories for specific projects'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no database changes)',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode - no changes will be made'))
        
        # Specific projects that need cleanup
        project_ids = ['Z34', 'Z31', 'Z30', 'Z28', 'Z25', 'Z24', 'Z12', 'Z11', 'Z7', 'Z6', 'Z5', 'Z4']
        
        deleted_count = 0
        
        with transaction.atomic():
            for hs_id in project_ids:
                try:
                    project = Project.objects.get(hs_id=hs_id)
                    
                    # Find Sales Confirmation histories that DON'T have "(fixed)" in comments
                    duplicate_histories = project.status_history.filter(
                        status__name__icontains='sales confirmation'
                    ).exclude(
                        comments__icontains='(fixed)'
                    )
                    
                    for history in duplicate_histories:
                        self.stdout.write(f'Project {hs_id}: Found duplicate Sales Confirmation from {history.changed_at.date()}')
                        
                        if not dry_run:
                            self.stdout.write(f'  Deleting: {history.status.name} - {history.changed_at} - "{history.comments}"')
                            history.delete()
                            deleted_count += 1
                        else:
                            self.stdout.write(f'  Would delete: {history.status.name} - {history.changed_at} - "{history.comments}"')
                            deleted_count += 1
                    
                    if not duplicate_histories:
                        self.stdout.write(f'Project {hs_id}: No duplicate histories found')
                        
                except Project.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Project {hs_id} not found'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing {hs_id}: {str(e)}'))
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN: Would delete {deleted_count} duplicate histories'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} duplicate histories')) 