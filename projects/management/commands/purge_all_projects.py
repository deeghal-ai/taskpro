from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project

class Command(BaseCommand):
    help = 'Deletes ALL projects and their associated status histories from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='You must add this flag to confirm you want to delete all project data.'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('❌ This is a destructive command. You must use the --confirm flag to proceed.'))
            return

        self.stdout.write(self.style.WARNING('🔥🔥🔥 DELETING ALL PROJECTS AND PROJECT STATUS HISTORIES... 🔥🔥🔥'))
        
        with transaction.atomic():
            # This will also delete all related ProjectStatusHistory records due to cascading deletes.
            project_count, _ = Project.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {project_count} projects.'))
        
        self.stdout.write('🎉 Purge process finished. The database is now clean.')