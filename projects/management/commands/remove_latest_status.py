from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project

class Command(BaseCommand):
    help = 'Finds and deletes the single most recent status history record for each project.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows which history records would be deleted without saving changes.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No records will be deleted ==='))

        self.stdout.write(self.style.SUCCESS('🚀 Starting to find and remove latest status records...'))
        
        projects_to_check = Project.objects.prefetch_related('status_history').all()
        histories_to_delete_pks = []

        for project in projects_to_check:
            # We only act if there's more than one history record
            if project.status_history.count() > 1:
                latest_history = project.status_history.order_by('-changed_at').first()
                if latest_history:
                    histories_to_delete_pks.append(latest_history.pk)
                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] Would delete status '{latest_history.status.name}' from {latest_history.changed_at.strftime('%Y-%m-%d')} for Project {project.hs_id}")

        self.stdout.write(f'Found {len(histories_to_delete_pks)} incorrect status records to remove.')

        if not dry_run and histories_to_delete_pks:
            self.stdout.write('Deleting records from the database...')
            with transaction.atomic():
                from projects.models import ProjectStatusHistory
                deleted_count, _ = ProjectStatusHistory.objects.filter(pk__in=histories_to_delete_pks).delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} status records.'))
        elif dry_run:
             self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETE: The records listed above would be deleted.'))
        else:
            self.stdout.write(self.style.SUCCESS('No records needed to be deleted.'))

        self.stdout.write('🎉 Status cleanup process finished.')