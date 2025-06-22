from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project
from accounts.models import User

class Command(BaseCommand):
    help = 'Deletes all projects assigned to a specific DPM.'

    def add_arguments(self, parser):
        parser.add_argument('dpm_username', type=str, help="The username of the DPM whose projects will be deleted.")
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='You must add this flag to confirm you want to delete these projects.'
        )

    def handle(self, *args, **options):
        dpm_username = options['dpm_username']
        
        if not options['confirm']:
            self.stdout.write(self.style.ERROR(f'❌ This is a destructive command. You must use the --confirm flag to delete projects for {dpm_username}.'))
            return

        try:
            dpm_user = User.objects.get(username=dpm_username, role='DPM')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ DPM user "{dpm_username}" not found.'))
            return

        self.stdout.write(self.style.WARNING(f'🔥🔥🔥 Finding all projects for DPM: {dpm_user.get_full_name()}... 🔥🔥🔥'))
        
        projects_to_delete = Project.objects.filter(dpm=dpm_user)
        project_count = projects_to_delete.count()

        if project_count == 0:
            self.stdout.write(self.style.SUCCESS(f'✅ No projects found for {dpm_username}. No action taken.'))
            return

        with transaction.atomic():
            self.stdout.write(self.style.WARNING(f'DELETING {project_count} projects...'))
            deleted_count, _ = projects_to_delete.delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} projects.'))
        
        self.stdout.write('🎉 DPM project purge finished.')