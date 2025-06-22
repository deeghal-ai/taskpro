from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project, ProjectStatusHistory

class Command(BaseCommand):
    help = 'Deletes all projects that were imported from the CSV files, along with their status histories.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows how many projects and histories would be deleted without actually deleting them.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No data will be deleted ==='))

        self.stdout.write(self.style.SUCCESS('🚀 Finding imported data to purge...'))
        
        # We identify imported projects by looking for the comment we added to their histories.
        # This is safer than deleting all projects.
        imported_project_ids = ProjectStatusHistory.objects.filter(
            comments='Imported from CSV'
        ).values_list('project_id', flat=True).distinct()

        projects_to_delete = Project.objects.filter(id__in=imported_project_ids)
        project_count = projects_to_delete.count()
        
        # Because of cascading deletes, we don't need to count histories separately.
        # Deleting the project will delete its associated status history.
        
        self.stdout.write(f'Found {project_count} imported projects to delete.')

        if project_count == 0:
            self.stdout.write(self.style.WARNING('No imported projects found to delete.'))
            return

        if not dry_run:
            self.stdout.write(self.style.WARNING(f'DELETING {project_count} projects and their associated data...'))
            with transaction.atomic():
                deleted_count, _ = projects_to_delete.delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} projects.'))
        else:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN COMPLETE: {project_count} projects and their histories would be deleted.'))
            
        self.stdout.write('🎉 Purge process finished.')