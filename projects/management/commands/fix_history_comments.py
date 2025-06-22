from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project, ProjectStatusHistory

class Command(BaseCommand):
    help = "One-time fix to add 'Imported from CSV' comment to all but the most recent status history for each project."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows which history records would be updated without saving changes.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No changes will be saved ==='))

        self.stdout.write(self.style.SUCCESS('🚀 Starting to fix status history comments...'))
        
        histories_to_update_pks = []

        all_projects = Project.objects.prefetch_related('status_history').all()
        total_projects = all_projects.count()
        self.stdout.write(f'Found {total_projects} projects to process.')

        for i, project in enumerate(all_projects):
            if i > 0 and i % 100 == 0:
                self.stdout.write(f'  📊 Processing project {i}/{total_projects}...')

            # Get all histories, ordered by most recent first
            all_project_histories = project.status_history.order_by('-changed_at')

            if all_project_histories.count() > 1:
                # The first one is the most recent (likely auto-created), skip it.
                # Update all the others.
                histories_to_update = all_project_histories[1:]
                for history in histories_to_update:
                    if history.comments != 'Imported from CSV':
                        histories_to_update_pks.append(history.pk)

        self.stdout.write(f'Found {len(histories_to_update_pks)} history records to update.')

        if not dry_run:
            self.stdout.write('Updating records in the database...')
            with transaction.atomic():
                updated_count = ProjectStatusHistory.objects.filter(pk__in=histories_to_update_pks).update(comments='Imported from CSV')
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully updated {updated_count} history records.'))
        else:
            self.stdout.write(self.style.WARNING('\\nDRY RUN COMPLETE: The above records would be updated.'))
            
        self.stdout.write('🎉 Comment fixing process finished.')