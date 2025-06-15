import csv
from django.core.management.base import BaseCommand
from accounts.models import User
from projects.models import Project
from django.db import transaction

class Command(BaseCommand):
    help = 'Updates the DPM for existing projects from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('--projects-csv', type=str, help='The path to the projects CSV file.', default='Projects.csv')
        parser.add_argument('--dry-run', action='store_true', help='Simulate the script without making database changes.')

    def handle(self, *args, **options):
        projects_csv_path = options['projects_csv']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN MODE - No changes will be made to the database ***'))

        # Load users into a dictionary for efficient lookup using their first name
        self.stdout.write("Loading users from the database (matching by first name)...")
        users = {user.first_name.lower(): user for user in User.objects.filter(is_active=True)}
        self.stdout.write(f"Loaded {len(users)} active users.")
        
        # Load the default DPM as a fallback
        default_dpm = None
        try:
            default_dpm = User.objects.get(email='sunny.bhaumik@studiomesmer.com')
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING("Default DPM 'sunny.bhaumik@studiomesmer.com' not found. The script will only update projects where the DPM is found in the CSV."))

        updated_count = 0
        not_found_count = 0
        dpm_not_found_count = 0
        
        try:
            with open(projects_csv_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                
                projects_to_update = []

                for i, row in enumerate(reader):
                    row_num = i + 2
                    hs_id = row.get('HS_ID', '').strip()
                    dpm_name = row.get('APM \nName', '').strip()
                    
                    if not hs_id:
                        continue

                    try:
                        project = Project.objects.get(hs_id=hs_id)
                        
                        target_dpm = users.get(dpm_name.lower())
                        
                        if target_dpm:
                            if project.dpm != target_dpm:
                                project.dpm = target_dpm
                                projects_to_update.append(project)
                                updated_count += 1
                        else:
                            if dpm_name:
                                dpm_not_found_count += 1

                    except Project.DoesNotExist:
                        not_found_count += 1
                
                if not dry_run:
                    self.stdout.write(f"Updating {len(projects_to_update)} projects in the database...")
                    with transaction.atomic():
                        Project.objects.bulk_update(projects_to_update, ['dpm'])
                    self.stdout.write(self.style.SUCCESS("Database update complete."))
                else:
                    self.stdout.write(self.style.WARNING("Dry run complete. No database changes were made."))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: The file '{projects_csv_path}' was not found."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"\n--- Summary ---"))
        self.stdout.write(f"Projects to be updated: {updated_count}")
        self.stdout.write(self.style.WARNING(f"Projects found in CSV but not in DB: {not_found_count}"))
        self.stdout.write(self.style.WARNING(f"DPMs found in CSV but not in DB: {dpm_not_found_count}")) 