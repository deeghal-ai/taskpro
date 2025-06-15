import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates the Account Manager for existing projects from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file-path',
            type=str,
            default='Projects.csv',
            help='The path to the projects CSV file.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Runs the script without saving any changes to the database.'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        is_dry_run = options['dry_run']

        if is_dry_run:
            self.stdout.write(self.style.WARNING('--- DRY RUN MODE ---'))
            self.stdout.write(self.style.WARNING('No changes will be saved to the database.'))

        self.stdout.write(self.style.SUCCESS(f'Starting Account Manager update from "{file_path}"...'))

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                projects_to_update = []
                
                for row in reader:
                    hs_id = row.get('HS_ID')
                    sales_person = row.get('Sales')

                    if not hs_id or not sales_person:
                        logger.warning(f"Skipping row due to missing HS_ID or Sales field: {row}")
                        continue

                    try:
                        project = Project.objects.get(hs_id=hs_id)
                        
                        # Check if an update is needed
                        if project.account_manager != sales_person.strip():
                            old_manager = project.account_manager
                            project.account_manager = sales_person.strip()
                            projects_to_update.append(project)
                            self.stdout.write(
                                f"  [PENDING] Project {hs_id}: "
                                f"Account Manager will be changed from '{old_manager}' "
                                f"to '{project.account_manager}'"
                            )
                        else:
                             self.stdout.write(
                                f"  [NO CHANGE] Project {hs_id}: "
                                f"Account Manager is already '{sales_person.strip()}'"
                            )

                    except Project.DoesNotExist:
                        logger.warning(f"Project with HS_ID '{hs_id}' not found in the database. Skipping.")
                        continue
                
                if not projects_to_update:
                    self.stdout.write(self.style.SUCCESS('No projects needed an update.'))
                    return

                self.stdout.write(self.style.SUCCESS(f'\nFound {len(projects_to_update)} projects to update.'))

                if not is_dry_run:
                    self.stdout.write(self.style.SUCCESS('Saving changes to the database...'))
                    with transaction.atomic():
                        Project.objects.bulk_update(projects_to_update, ['account_manager'])
                    self.stdout.write(self.style.SUCCESS('Successfully updated all projects.'))
                else:
                    self.stdout.write(self.style.WARNING('\n--- DRY RUN COMPLETE ---'))
                    self.stdout.write(self.style.WARNING('No changes were saved.'))


        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Error: The file "{file_path}" was not found.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred: {e}')) 