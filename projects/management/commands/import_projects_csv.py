import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import (
    Project, Product, ProductSubcategory, ProjectStatusOption, 
    ProjectStatusHistory
)
from locations.models import City, Region
from accounts.models import User

# Attempt to import dateutil, provide guidance if not found
try:
    from dateutil.parser import parse as dateutil_parse
except ImportError:
    dateutil_parse = None

class Command(BaseCommand):
    help = 'Import projects and status histories from CSV files with detailed logging.'

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

    def handle(self, *args, **options):
        projects_csv = options['projects_csv']
        statuses_csv = options['statuses_csv']
        dry_run = options['dry_run']
        
        if dateutil_parse is None:
            self.stdout.write(self.style.ERROR(
                "The 'python-dateutil' library is required. "
                "Please install it by running: pip install python-dateutil"
            ))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING('*** DRY RUN MODE - No changes will be made to the database ***')
            )
        
        # Check if files exist
        if not os.path.exists(projects_csv):
            self.stdout.write(self.style.ERROR(f'Projects CSV file not found: {projects_csv}'))
            return
            
        if not os.path.exists(statuses_csv):
            self.stdout.write(self.style.ERROR(f'Statuses CSV file not found: {statuses_csv}'))
            return

        # Pre-load lookup data
        self.stdout.write("Loading lookup data from the database...")
        self.load_lookup_data()
        
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            sid = transaction.savepoint() # Create a savepoint
            
            try:
                # Import projects first, and get a dictionary of the projects to be created
                projects_to_create, project_errors = self.import_projects(projects_csv)
                
                # Create a dictionary for the status importer
                # In a real run, these are saved. In a dry run, they are in-memory.
                projects_dict = {p.hs_id: p for p in projects_to_create}
                
                # Then import status histories for ONLY the projects we just processed
                statuses_to_create, status_errors = self.import_status_histories(
                    statuses_csv, projects_dict
                )
                
                summary_style = self.style.SUCCESS if not dry_run else self.style.WARNING
                
                self.stdout.write(summary_style("\n" + "="*20 + " IMPORT SUMMARY " + "="*20))
                self.stdout.write(summary_style(f"Projects to be created: {len(projects_to_create)}"))
                self.stdout.write(self.style.ERROR(f"Project import errors: {len(project_errors)}"))
                for err in project_errors[:10]: # Show first 10 errors
                    self.stdout.write(self.style.ERROR(f"  - {err}"))

                self.stdout.write(summary_style(f"Status histories to be created: {len(statuses_to_create)}"))
                self.stdout.write(self.style.ERROR(f"Status import errors: {len(status_errors)}"))
                for err in status_errors[:10]: # Show first 10 errors
                    self.stdout.write(self.style.ERROR(f"  - {err}"))
                self.stdout.write(summary_style("="*58 + "\n"))

                if dry_run:
                    transaction.savepoint_rollback(sid)
                    self.stdout.write(self.style.WARNING('DRY RUN COMPLETE. No data was changed.'))
                else:
                    # Perform the actual bulk creation if not a dry run
                    if projects_to_create:
                        Project.objects.bulk_create(projects_to_create, batch_size=500)
                        self.stdout.write(self.style.SUCCESS(f"Successfully created {len(projects_to_create)} projects."))
                        
                        # Re-fetch the projects we just created to get their DB IDs
                        created_projects_dict = {p.hs_id: p for p in Project.objects.filter(hs_id__in=projects_dict.keys())}
                        
                        # Now, update the status history objects with the correct project instances
                        final_histories = []
                        for hs in statuses_to_create:
                            if hs.project.hs_id in created_projects_dict:
                                hs.project = created_projects_dict[hs.project.hs_id]
                                final_histories.append(hs)

                        if final_histories:
                            ProjectStatusHistory.objects.bulk_create(final_histories, batch_size=500, ignore_conflicts=True)
                            self.stdout.write(self.style.SUCCESS(f"Successfully created {len(final_histories)} status history entries."))
                            
                    transaction.savepoint_commit(sid)
                    self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE. Data has been saved to the database.'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'A critical error occurred: {str(e)}'))
                transaction.savepoint_rollback(sid)
                self.stdout.write(self.style.ERROR('Transaction has been rolled back. No data was changed.'))
                if not dry_run:
                    raise

    def load_lookup_data(self):
        """Pre-load all lookup data for better performance"""
        self.products = {p.name.strip().lower(): p for p in Product.objects.all()}
        self.cities = {c.name.strip().lower(): c for c in City.objects.all()}
        self.users = {u.username.strip().lower(): u for u in User.objects.all()}
        self.statuses = {s.name.strip().lower(): s for s in ProjectStatusOption.objects.all()}
        self.subcategories = {sc.name.strip().lower(): sc for sc in ProductSubcategory.objects.all()}
        
        # Get a default DPM (first available)
        self.default_dpm = User.objects.filter(role='DPM').first()
        if not self.default_dpm:
            raise Exception("CRITICAL: No DPM users found in the system. Please create a DPM user first.")
            
        # Get a default region and city (first available)  
        self.default_region = Region.objects.first()
        if not self.default_region:
            raise Exception("CRITICAL: No Regions found in the system. Please create at least one Region first.")
            
        self.default_city = City.objects.first()
        if not self.default_city:
            # If no city exists, create one to use as a default
            self.default_city = City.objects.create(name="Default City", region=self.default_region)
            self.stdout.write(self.style.WARNING("No cities found. Created a 'Default City' to proceed."))

        self.stdout.write("  - Loading cities...")
        self.cities = {city.name.lower(): city for city in City.objects.all()}
        self.stdout.write(f"    - Loaded {len(self.cities)} cities.")

        self.stdout.write("  - Loading users...")
        self.users = {f"{user.first_name} {user.last_name}".lower(): user for user in User.objects.filter(is_active=True)}
        self.stdout.write(f"    - Loaded {len(self.users)} active users.")

    def get_or_create_city(self, city_name):
        city_name = city_name.strip()
        if not city_name:
            return self.default_city
        
        city_key = city_name.lower()
        if city_key in self.cities:
            return self.cities[city_key]
        
        city, created = City.objects.get_or_create(
            name__iexact=city_name, 
            defaults={'name': city_name, 'region': self.default_region}
        )
        if created:
            self.cities[city_key] = city
            self.stdout.write(f'  [INFO] Created new city: {city_name}')
        return city

    def get_or_create_subcategory(self, subcat_name):
        subcat_name = subcat_name.strip()
        if not subcat_name:
            return None
            
        subcat_key = subcat_name.lower()
        if subcat_key in self.subcategories:
            return self.subcategories[subcat_key]
        
        subcat, created = ProductSubcategory.objects.get_or_create(name__iexact=subcat_name, defaults={'name': subcat_name})
        if created:
            self.subcategories[subcat_key] = subcat
            self.stdout.write(f'  [INFO] Created new product subcategory: {subcat_name}')
        return subcat

    def safe_int(self, value, default=1):
        try:
            return int(float(str(value).strip())) if value and str(value).strip() else default
        except (ValueError, TypeError):
            return default

    def safe_date(self, date_str, default_date=None):
        date_str = str(date_str).strip()
        if not date_str:
            return default_date or datetime.now().date()
        try:
            return dateutil_parse(date_str).date()
        except Exception:
            return default_date or datetime.now().date()

    def import_projects(self, csv_file):
        self.stdout.write("\n--- Starting Project Import ---")
        projects_to_create = []
        errors = []
        existing_hs_ids = set(Project.objects.values_list('hs_id', flat=True))
        
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                row_num = i + 2
                hs_id = row.get('HS_ID', '').strip()
                
                if not hs_id:
                    errors.append(f"Row {row_num}: Skipped (Empty HS_ID)")
                    continue
                
                if hs_id in existing_hs_ids:
                    # errors.append(f"Row {row_num}: Skipped (Project with HS_ID '{hs_id}' already exists)")
                    continue
                
                if row_num % 10 == 0:
                    self.stdout.write(f"  ...processing project row {row_num}")
                
                try:
                    product_name_raw = row.get('HS _Product', '').strip() or row.get('HS_Product', '').strip()
                    product_name = product_name_raw.lower() if product_name_raw else ''
                    if not product_name:
                        errors.append(f"Row {row_num} (HS_ID: {hs_id}): Skipped (No product specified)")
                        continue
                    
                    product = self.products.get(product_name)
                    if not product:
                        errors.append(f"Row {row_num} (HS_ID: {hs_id}): Skipped (Product '{product_name_raw}' not found)")
                        continue
                    
                    status_name_raw = row.get('Status', '').strip()
                    status_name = status_name_raw.lower()
                    current_status = self.statuses.get(status_name) if status_name else list(self.statuses.values())[0]
                    if not current_status:
                        errors.append(f"Row {row_num} (HS_ID: {hs_id}): Warning (Status '{status_name_raw}' not found, using default)")
                        current_status = list(self.statuses.values())[0]

                    # Get the DPM from the CSV, with a fallback to the default DPM
                    dpm_name_raw = row.get('apm name', '').strip()
                    dpm_user = self.users.get(dpm_name_raw.lower())

                    if not dpm_user and dpm_name_raw:
                        errors.append(f"Row {row_num} (HS_ID: {hs_id}): Warning (DPM '{dpm_name_raw}' not found, using default)")
                    
                    dpm_to_assign = dpm_user or self.default_dpm

                    projects_to_create.append(Project(
                        hs_id=hs_id,
                        opportunity_id=row.get('Opp ID', '').strip(),
                        project_type=row.get('Event/\nNon-Event', '').strip(),
                        project_name=(row.get('Project \nName') or row.get('Builder') or hs_id).strip(),
                        builder_name=(row.get('Builder') or 'Unknown Builder').strip(),
                        city=self.get_or_create_city(row.get('City')),
                        product=product,
                        product_subcategory=self.get_or_create_subcategory(row.get('Product_Sub_\ncategory')),
                        package_id=row.get('Package_ID', '').strip(),
                        quantity=self.safe_int(row.get('Quantity'), 1),
                        purchase_date=self.safe_date(row.get('Latest_Date')),
                        sales_confirmation_date=self.safe_date(row.get('Latest_Date')),
                        expected_tat=self.safe_int(row.get('Expected TAT'), product.expected_tat),
                        account_manager=(row.get('Sales') or 'Unknown').strip(),
                        dpm=dpm_to_assign,
                        current_status=current_status
                    ))
                except Exception as e:
                    errors.append(f"Row {row_num} (HS_ID: {hs_id}): CRITICAL ERROR - {str(e)}")
        
        return projects_to_create, errors

    def import_status_histories(self, csv_file, projects_dict):
        self.stdout.write("\n--- Starting Status History Import (Grouping by Project) ---")
        histories_to_create = []
        errors = []
        
        if not projects_dict:
            self.stdout.write(self.style.WARNING("No projects to process. Skipping status history import."))
            return [], errors

        # 1. Read and group all statuses by HS_ID first
        self.stdout.write("  ...reading and grouping all status entries by project...")
        statuses_by_hs_id = {}
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hs_id = row.get('HS_ID', '').strip()
                if hs_id:
                    if hs_id not in statuses_by_hs_id:
                        statuses_by_hs_id[hs_id] = []
                    statuses_by_hs_id[hs_id].append(row)
        self.stdout.write(f"  ...found status entries for {len(statuses_by_hs_id)} unique projects in the CSV.")

        # 2. Iterate through the projects that were actually created
        self.stdout.write("  ...matching statuses to the projects being imported...")
        
        for hs_id, project in projects_dict.items():
            if hs_id in statuses_by_hs_id:
                for status_row in statuses_by_hs_id[hs_id]:
                    status_name_raw = status_row.get('Status', '').strip()
                    date_str = status_row.get('Date', '').strip()

                    if not status_name_raw or not date_str:
                        continue
                    
                    status_name = status_name_raw.lower()
                    status = self.statuses.get(status_name)
                    if not status:
                        errors.append(f"Row for HS_ID '{hs_id}': Skipped (Status '{status_name_raw}' not found)")
                        continue
                    
                    try:
                        changed_at = self.safe_date(date_str)
                        
                        # Add to list for bulk creation
                        histories_to_create.append(ProjectStatusHistory(
                            project=project, # This is an in-memory object
                            status=status,
                            category_one_snapshot=status.category_one,
                            category_two_snapshot=status.category_two,
                            changed_by=self.default_dpm,
                            changed_at=datetime.combine(changed_at, datetime.min.time()),
                            comments=f'Imported from CSV on {datetime.now().strftime("%Y-%m-%d")}'
                        ))
                    except Exception as e:
                        errors.append(f"Row for HS_ID '{hs_id}': CRITICAL ERROR - {str(e)}")
        
        self.stdout.write(f"  ...found {len(histories_to_create)} matching status entries to import.")
        return histories_to_create, errors 