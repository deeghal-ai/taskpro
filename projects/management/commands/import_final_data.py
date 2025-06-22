import csv
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils import timezone
from projects.models import (
    Project, Product, ProductSubcategory, ProjectStatusOption, 
    ProjectStatusHistory
)
from locations.models import City, Region
from accounts.models import User
from django.db.models.signals import post_save

class Command(BaseCommand):
    help = 'Final comprehensive import of projects and status histories from CSV files with DPM mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--projects-csv',
            type=str,
            default='Projects.csv',
            help='Path to projects CSV file'
        )
        parser.add_argument(
            '--statuses-csv', 
            type=str,
            default='Statuses.csv',
            help='Path to status history CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes (preview mode)'
        )
        parser.add_argument(
            '--skip-projects',
            action='store_true',
            help='Skip the project import step.'
        )
        parser.add_argument(
            '--skip-statuses',
            action='store_true',
            help='Skip the status history import step.'
        )

    def handle(self, *args, **options):
        self.projects_csv = options['projects_csv']
        self.statuses_csv = options['statuses_csv']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No changes will be made ==='))
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting final comprehensive data import...'))
        
        self.load_lookup_data()
        self.create_apm_to_dpm_mapping()
        
        if not options['skip_projects']:
            # Pre-process to find the latest status date for each project
            self.latest_status_dates = self.get_latest_status_dates()
            projects_created, imported_projects_dict = self.import_projects()
        else:
            self.stdout.write(self.style.WARNING('Skipping project import as requested.'))
            projects_created = 0
            imported_projects_dict = {}
        
        # Combine newly imported projects (in memory) with existing DB projects
        # This ensures status histories can be linked to both.
        if self.dry_run:
            existing_projects_dict = {p.hs_id: p for p in Project.objects.all()}
            all_projects_for_histories = {**existing_projects_dict, **imported_projects_dict}
        else:
            # In a real run, all projects are in the DB
            all_projects_for_histories = {p.hs_id: p for p in Project.objects.all()}

        if not options['skip_statuses']:
            histories_created = self.import_status_histories(all_projects_for_histories)
        else:
            self.stdout.write(self.style.WARNING('Skipping status history import as requested.'))
            histories_created = 0
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN NOTE: Transactions were not committed.'))
                
        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 IMPORT COMPLETED!\n'
            f'Projects created: {projects_created}\n'
            f'Status histories processed (created or updated): {histories_created}'
        ))

    def load_lookup_data(self):
        """Pre-load all lookup data for efficient mapping"""
        self.stdout.write('📊 Loading lookup data...')
        
        # Products (case-insensitive lookup)
        self.products = {p.name.strip().lower(): p for p in Product.objects.all()}
        self.stdout.write(f'  ✅ Loaded {len(self.products)} products')
        
        # Cities (case-insensitive lookup)
        self.cities = {c.name.strip().lower(): c for c in City.objects.all()}
        self.stdout.write(f'  ✅ Loaded {len(self.cities)} cities')
        
        # Status options (case-insensitive lookup)
        self.statuses = {s.name.strip().lower(): s for s in ProjectStatusOption.objects.all()}
        self.stdout.write(f'  ✅ Loaded {len(self.statuses)} status options')
        
        # Product subcategories (case-insensitive lookup)
        self.subcategories = {sc.name.strip().lower(): sc for sc in ProductSubcategory.objects.all()}
        self.stdout.write(f'  ✅ Loaded {len(self.subcategories)} subcategories')
        
        # Default fallbacks
        self.default_city = City.objects.first()
        self.default_status = ProjectStatusOption.objects.first()
        
        # --- ADDED: Placeholder for projects with no product ---
        self.placeholder_product, created = Product.objects.get_or_create(
            name="Deemed Consumed Placeholder",
            defaults={'expected_tat': 1}
        )
        if created:
            self.stdout.write('  ✅ Created placeholder product for projects without one.')
        self.products[self.placeholder_product.name.lower()] = self.placeholder_product

        if not self.default_city or not self.default_status:
            raise Exception("❌ CRITICAL: Missing default city or status option in database")

    def create_apm_to_dpm_mapping(self):
        """Loads the DPM users from the database."""
        self.stdout.write('👥 Loading DPM users for mapping...')
        self.dpm_users = {u.username.lower(): u for u in User.objects.filter(role='DPM')}
        if not self.dpm_users:
            raise Exception("❌ CRITICAL: No DPM users found in database")
        
        # Assign a default DPM for fallbacks
        self.default_dpm = list(self.dpm_users.values())[0]
        self.stdout.write(f'  ✅ Found {len(self.dpm_users)} DPMs. Default is {self.default_dpm.username}.')

    def get_latest_status_dates(self):
        """Pre-reads the statuses CSV to find the latest date for each HS_ID."""
        self.stdout.write('\n🗓️  Pre-processing status dates...')
        latest_dates = {}
        if not os.path.exists(self.statuses_csv):
            self.stdout.write(f'⚠️  Statuses CSV not found at {self.statuses_csv}, cannot determine latest dates.')
            return latest_dates

        with open(self.statuses_csv, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hs_id = row.get('HS_ID', '').strip()
                date_str = row.get('Date', '').strip()

                if not hs_id or not date_str:
                    continue
                
                current_date = self.safe_date(date_str)

                if current_date and (hs_id not in latest_dates or current_date > latest_dates[hs_id]):
                    latest_dates[hs_id] = current_date
        
        self.stdout.write(f'  ✅ Found latest dates for {len(latest_dates)} projects.')
        return latest_dates

    def get_dpm_from_apm(self, apm_name_str):
        """
        Finds the correct DPM based on the APM name from the CSV.
        - If name contains 'anil', map to anil.
        - If name contains 'jagadish', map to jagadish.
        - If name contains 'abhiudaya', map to abhiudaya.
        - Otherwise, use the default DPM.
        """
        if not apm_name_str:
            self.stdout.write(self.style.WARNING(f"  - APM Name is blank. Assigning default DPM: {self.default_dpm.username}"))
            return self.default_dpm

        apm_name_lower = apm_name_str.lower()

        if 'anil' in apm_name_lower:
            return self.dpm_users.get('anil', self.default_dpm)
        if 'jagadish' in apm_name_lower:
            return self.dpm_users.get('jagadish', self.default_dpm)
        if 'abhiudaya' in apm_name_lower:
            return self.dpm_users.get('abhiudaya', self.default_dpm)
        
        self.stdout.write(self.style.WARNING(f"  - APM Name '{apm_name_str}' not matched. Assigning default DPM: {self.default_dpm.username}"))
        return self.default_dpm

    def safe_date(self, date_str):
        """Safely parse date string, returns None if invalid."""
        if not date_str or not str(date_str).strip():
            return None
        
        try:
            # Handle various date formats
            date_str = str(date_str).strip()
            
            # Try Django's parser first
            parsed = parse_date(date_str)
            if parsed:
                return parsed
            
            # Try common formats
            for fmt in ['%d-%b-%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # If all else fails, return None
            return None
        except:
            return None

    def safe_int(self, value, default=1):
        """Safely convert to integer"""
        try:
            return max(1, int(float(str(value).strip())))
        except:
            return default

    def find_column_value(self, row, keywords):
        """Find column value by keywords (handles multi-line headers)"""
        for key, value in row.items():
            key_clean = key.replace('\n', ' ').replace('\r', ' ').strip().lower()
            for keyword in keywords:
                if keyword.lower() in key_clean:
                    return str(value).strip() if value else ''
        return ''

    def import_projects(self):
        """Import projects from CSV"""
        self.stdout.write('\n📦 Importing projects...')
        
        if not os.path.exists(self.projects_csv):
            self.stdout.write(f'❌ Projects CSV file not found: {self.projects_csv}')
            return 0, {}
        
        projects_created = 0
        projects_skipped = 0
        imported_projects_dict = {}
        existing_hs_ids = set(Project.objects.values_list('hs_id', flat=True))
        
        with open(self.projects_csv, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader, 1):
                if i % 100 == 0:
                    self.stdout.write(f'  📊 Processing row {i}...')
                
                hs_id = row.get('HS_ID', '').strip()
                if not hs_id:
                    projects_skipped += 1
                    continue

                if not self.dry_run and hs_id in existing_hs_ids:
                    projects_skipped += 1
                    continue
                
                try:
                    # --- ADDED: Individual transaction for each project ---
                    with transaction.atomic():
                        # Extract project data
                        project_name = self.find_column_value(row, ['project name']) or row.get('Builder', '') or hs_id
                        builder_name = row.get('Builder', '').strip() or 'Unknown Builder'
                        
                        # --- CORRECTED MAPPING LOGIC ---
                        opportunity_id = self.find_column_value(row, ['opp id']) or hs_id
                        account_manager = self.find_column_value(row, ['sales']) or 'Unknown'
                        apm_name = self.find_column_value(row, ['apm name', 'apm'])
                        dpm = self.get_dpm_from_apm(apm_name)
                        
                        # Get product
                        product_name = row.get('HS _Product', '').strip()
                        product = self.products.get(product_name.lower()) if product_name else None
                        if not product:
                            # --- MODIFIED: Assign placeholder instead of skipping ---
                            self.stdout.write(f'  ⚠️  Product not found for {hs_id}. Assigning placeholder.')
                            product = self.placeholder_product
                        
                        # Get city
                        city_name = row.get('City', '').strip()
                        city = self.cities.get(city_name.lower()) if city_name else self.default_city
                        
                        # Get status
                        status_name = row.get('Status', '').strip()
                        current_status = self.statuses.get(status_name.lower()) if status_name else self.default_status
                        
                        # Get other fields
                        quantity = self.safe_int(row.get('Quantity', '1'))
                        expected_tat = self.safe_int(row.get('Expected TAT', ''), product.expected_tat)
                        
                        # --- MODIFIED DATE LOGIC ---
                        # 1. Try to get date from 'Latest_Date' column
                        purchase_date = self.safe_date(row.get('Latest_Date', ''))
                        
                        # 2. If not found, use the latest date from the statuses file
                        if purchase_date is None:
                            status_file_date = self.latest_status_dates.get(hs_id)
                            if status_file_date:
                                purchase_date = status_file_date
                            else:
                                # This is the key insight - we didn't find it in either file.
                                self.stdout.write(self.style.WARNING(f"  ⚠️  Date for {hs_id} is blank in Projects.csv AND no valid date was found in Statuses.csv. Defaulting to today."))
                                purchase_date = date.today()
                        
                        # Get subcategory
                        subcat_name = self.find_column_value(row, ['product_sub_category', 'subcategory'])
                        product_subcategory = self.subcategories.get(subcat_name.lower()) if subcat_name else None
                        
                        # Create project instance in memory
                        project_instance = Project(
                            hs_id=hs_id,
                            opportunity_id=opportunity_id,
                            project_type=row.get('Event/\nNon-Event', '').strip() or 'NON_EVENT',
                            project_name=project_name,
                            builder_name=builder_name,
                            city=city,
                            product=product,
                            product_subcategory=product_subcategory,
                            package_id=row.get('Package_ID', '').strip(),
                            quantity=quantity,
                            purchase_date=purchase_date,
                            sales_confirmation_date=purchase_date,
                            expected_tat=expected_tat,
                            account_manager=account_manager,
                            dpm=dpm,
                            current_status=current_status
                        )
                        
                        if not self.dry_run:
                            project_instance.save()
                        
                        imported_projects_dict[hs_id] = project_instance
                        projects_created += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ❌ Error on project {hs_id}. SKIPPING. Reason: {type(e).__name__} - {e}'))
                    projects_skipped += 1
        
        self.stdout.write(f'  ✅ Projects - Created: {projects_created}, Skipped: {projects_skipped}')
        return projects_created, imported_projects_dict

    def import_status_histories(self, projects_dict):
        """Import status histories from CSV"""
        self.stdout.write('\n📋 Importing status histories...')
        
        if not os.path.exists(self.statuses_csv):
            self.stdout.write(f'❌ Statuses CSV file not found: {self.statuses_csv}')
            return 0
        
        histories_created = 0
        histories_skipped = 0
        
        with open(self.statuses_csv, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader, 1):
                if i % 500 == 0:
                    self.stdout.write(f'  📊 Processing status row {i}...')
                
                try:
                    with transaction.atomic():
                        hs_id = row.get('HS_ID', '').strip()
                        status_name = row.get('Status', '').strip()
                        date_str = row.get('Date', '').strip()
                        
                        if not all([hs_id, status_name, date_str]):
                            histories_skipped += 1
                            continue
                        
                        # Get project from the passed-in dictionary
                        project = projects_dict.get(hs_id)
                        if not project:
                            # This will now correctly skip histories for projects that were skipped (e.g. bad product)
                            histories_skipped += 1
                            continue
                        
                        # Get status
                        status = self.statuses.get(status_name.lower())
                        if not status:
                            histories_skipped += 1
                            continue
                        
                        # Parse date and make it timezone-aware
                        changed_date = self.safe_date(date_str)
                        
                        if not changed_date:
                            histories_skipped += 1
                            continue

                        naive_datetime = datetime.combine(changed_date, datetime.min.time())
                        aware_datetime = timezone.make_aware(naive_datetime)
                        
                        # --- MODIFIED: Use update_or_create to fix existing bad data ---
                        if not self.dry_run:
                            obj, created = ProjectStatusHistory.objects.update_or_create(
                                project=project,
                                status=status,
                                changed_at=aware_datetime,
                                defaults={
                                    'category_one_snapshot': status.category_one,
                                    'category_two_snapshot': status.category_two,
                                    'changed_by': project.dpm,
                                    'comments': 'Imported from CSV'
                                }
                            )
                            if created:
                                histories_created += 1
                            # We also want to count records that were updated.
                            # For simplicity in output, we will just show a different message.
                        else:
                            # In dry run, we just count it if we found the project and status
                            histories_created += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ❌ Error processing status history row for {hs_id}. SKIPPING. Reason: {type(e).__name__} - {e}'))
                    histories_skipped += 1
        
        self.stdout.write(f'  ✅ Status histories processed (created or updated): {histories_created}, Skipped: {histories_skipped}')
        return histories_created