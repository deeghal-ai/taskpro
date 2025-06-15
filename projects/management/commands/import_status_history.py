import csv
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Project, ProjectStatusOption, ProjectStatusHistory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports historical project status data from a CSV file, starting from projects in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file-path',
            type=str,
            default='Statuses.csv',
            help='The path to the statuses CSV file.'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(self.style.SUCCESS(f'Starting status history import from "{file_path}"...'))

        # Step 1: Read the entire CSV into memory and group by HS_ID.
        self.stdout.write(self.style.SUCCESS('Reading and pre-processing CSV file...'))
        status_data_by_hs_id = defaultdict(list)
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    hs_id = row.get('HS_ID')
                    if hs_id:  # Only consider rows with an HS_ID
                        status_data_by_hs_id[hs_id].append(row)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Error: The file at "{file_path}" was not found.'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred during file processing: {e}'))
            return
            
        if not status_data_by_hs_id:
            self.stdout.write(self.style.WARNING('Could not find any data with HS_IDs in the CSV. Aborting.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found status data for {len(status_data_by_hs_id)} unique HS_IDs in the CSV.'))

        # Step 2: Iterate through DB projects and create history objects.
        statuses_cache = {s.name.lower(): s for s in ProjectStatusOption.objects.all()}
        history_to_create = []

        self.stdout.write(self.style.SUCCESS('Matching CSV data to projects in the database...'))
        projects = Project.objects.all()
        
        for project in projects:
            project_statuses = status_data_by_hs_id.get(project.hs_id)
            if not project_statuses:
                continue  # No history for this project in the CSV

            for row in project_statuses:
                status_name = row.get('Status')
                date_str = row.get('Date')

                if not all([status_name, date_str]):
                    logger.warning(f"Skipping status entry for project {project.hs_id} due to missing data: {row}")
                    continue

                status_option = statuses_cache.get(status_name.lower())
                if not status_option:
                    logger.warning(f"Status '{status_name}' not found. Skipping history record for project {project.hs_id}.")
                    continue
                
                try:
                    changed_at_date = datetime.strptime(date_str, '%d-%b-%Y').date()
                except ValueError:
                    logger.error(f"Could not parse date '{date_str}' for project {project.hs_id}. Skipping.")
                    continue
                
                history_to_create.append(
                    ProjectStatusHistory(
                        project=project,
                        status=status_option,
                        changed_at=changed_at_date,
                        changed_by=project.dpm,  # Defaulting to project's DPM
                        comments="Imported from historical CSV."
                    )
                )

        # Step 3: If we have valid records, perform DB operations in a single transaction.
        if history_to_create:
            self.stdout.write(self.style.SUCCESS(f'Matched and validated {len(history_to_create)} history records to import.'))
            try:
                with transaction.atomic():
                    self.stdout.write(self.style.WARNING('Deleting all existing project status history records...'))
                    ProjectStatusHistory.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS('Old history records deleted.'))

                    ProjectStatusHistory.objects.bulk_create(history_to_create)
                    self.stdout.write(self.style.SUCCESS('Successfully imported new status history records.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred during the database transaction. No changes were made. Error: {e}'))
                return
        else:
            self.stdout.write(self.style.WARNING('Could not match any status history from the CSV to projects in the database. No changes were made.'))

        self.stdout.write(self.style.SUCCESS('Status history import completed.')) 