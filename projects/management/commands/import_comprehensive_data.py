import csv
import os
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from projects.models import (
    Project, ProjectStatusHistory, ProjectStatusOption, Product, 
    ProductSubcategory, ProjectDelivery
)
from projects.signals import track_status_changes
from locations.models import City as LocationCity, Region as LocationRegion


class Command(BaseCommand):
    help = 'Import comprehensive project data from CSV files with optimizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable-signals', 
            action='store_true',
            help='Disable signals during import to avoid conflicts'
        )

    def handle(self, *args, **options):
        if options['disable_signals']:
            self.stdout.write("Disabling signals...")
            post_save.disconnect(track_status_changes, sender=ProjectStatusHistory)
        
        try:
            self.import_data()
        finally:
            if options['disable_signals']:
                self.stdout.write("Re-enabling signals...")
                post_save.connect(track_status_changes, sender=ProjectStatusHistory)

    @transaction.atomic
    def import_data(self):
        self.stdout.write("Starting comprehensive data import...")
        
        # Step 1: Import basic reference data
        self.import_regions_and_cities()
        self.import_products()
        self.import_project_statuses()
        self.import_users()
        
        # Step 2: Import projects with proper mappings
        self.import_projects()
        
        # Step 3: Import status history with latest date tracking
        self.import_status_history()
        
        # Step 4: Update project latest dates and current status
        self.update_project_metadata()
        
        self.stdout.write(self.style.SUCCESS("Data import completed successfully!"))

    def import_regions_and_cities(self):
        self.stdout.write("Importing regions and cities...")
        
        # Read unique cities from projects CSV
        cities_data = set()
        with open('Projects.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                city_name = row.get('City', '').strip()
                if city_name and city_name != 'City':
                    cities_data.add(city_name)
        
        # Create regions and cities with proper mapping
        region_mapping = {
            'Mumbai': 'West', 'Pune': 'West', 'Surat': 'West', 'Ahmedabad': 'West', 'Nashik': 'West',
            'Navi Mumbai': 'West', 'Gandhinagar': 'West', 'Jaipur': 'West',
            'Delhi': 'North', 'Noida': 'North', 'Gurgaon': 'North', 'Chandigarh': 'North', 
            'Faridabad': 'North', 'Mohali': 'North', 'Dehradun': 'North', 'Lucknow': 'North',
            'Bangalore': 'South', 'Chennai': 'South', 'Hyderabad': 'South', 'Coimbatore': 'South',
            'Visakhapatnam': 'South',
            'Bhubaneswar': 'East', 'Patna': 'East', 'Darbhanga': 'East', 'Varanasi': 'East',
            'Raipur': 'Central', 'Nagpur': 'Central', 'Durg': 'Central'
        }
        
        created_regions = {}
        for city_name in cities_data:
            region_name = region_mapping.get(city_name, 'Other')
            
            # Create region if not exists
            if region_name not in created_regions:
                region, created = LocationRegion.objects.get_or_create(
                    name=region_name,
                    defaults={'description': f'{region_name} Region'}
                )
                created_regions[region_name] = region
                if created:
                    self.stdout.write(f"Created region: {region_name}")
            
            # Create city
            city, created = LocationCity.objects.get_or_create(
                name=city_name,
                region=created_regions[region_name],
                defaults={'state': region_name}
            )
            if created:
                self.stdout.write(f"Created city: {city_name} in {region_name}")

    def import_products(self):
        self.stdout.write("Importing products...")
        
        products_data = set()
        with open('Projects.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                product_name = row.get('HS _Product', '').strip()
                if product_name and product_name != 'HS _Product':
                    products_data.add(product_name)
        
        for product_name in products_data:
            product, created = Product.objects.get_or_create(
                name=product_name,
                defaults={
                    'description': f'{product_name} product',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"Created product: {product_name}")

    def import_project_statuses(self):
        self.stdout.write("Importing project statuses...")
        
        statuses_data = set()
        
        # Get statuses from Projects.csv
        with open('Projects.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                status_name = row.get('Status', '').strip()
                if status_name and status_name != 'Status':
                    statuses_data.add(status_name)
        
        # Get statuses from Statuses.csv
        with open('Statuses.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                status_name = row.get('Status', '').strip()
                if status_name and status_name != 'Status':
                    statuses_data.add(status_name)
        
        # Status color mapping
        status_colors = {
            'Sales Confirmation': '#28a745',
            'Partial Data Received': '#17a2b8',
            'Project Start Date': '#6f42c1',
            'Tower Modeling Start': '#fd7e14',
            'Tower Modeling End': '#20c997',
            'Final Data Received': '#6610f2',
            '1st Cut Delivery': '#e83e8c',
            '1st Rework Received': '#ffc107',
            '1st Rework Start': '#fd7e14',
            '1st Rework End': '#20c997',
            'Final Delivery': '#28a745',
            'Deemed Consumed': '#6c757d',
            'Opp Dropped': '#dc3545',
            'Purchase Date': '#007bff',
            'Photoshoot Start': '#17a2b8',
            'Playblast Delivery': '#6f42c1',
            'Tower Modeling Confirmation': '#28a745'
        }
        
        for status_name in statuses_data:
            status, created = ProjectStatusOption.objects.get_or_create(
                name=status_name,
                defaults={
                    'category_one': 'Imported',
                    'category_two': 'From CSV',
                    'order': list(statuses_data).index(status_name),
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"Created status: {status_name}")

    def import_users(self):
        self.stdout.write("Importing users (DPMs and Account Managers)...")
        
        # Get APM names (to be mapped as DPMs) and Sales (to be mapped as Account Managers)
        apm_names = set()
        sales_names = set()
        
        with open('Projects.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                apm_name = row.get('APM Name', '').strip()
                sales_name = row.get('Sales', '').strip()
                
                if apm_name and apm_name not in ['APM Name', '']:
                    apm_names.add(apm_name)
                if sales_name and sales_name not in ['Sales', '']:
                    sales_names.add(sales_name)
        
        # Create DPM users (from APM Name column)
        for apm_name in apm_names:
            # Create username from name
            username = apm_name.lower().replace(' ', '_').replace('&', 'and')[:30]
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': apm_name.split()[0] if apm_name.split() else apm_name,
                    'last_name': ' '.join(apm_name.split()[1:]) if len(apm_name.split()) > 1 else '',
                    'email': f'{username}@company.com',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"Created DPM user: {apm_name} ({username})")
        
        self.stdout.write(f"Processed {len(apm_names)} DPMs and noted {len(sales_names)} Account Managers")

    def import_projects(self):
        self.stdout.write("Importing projects with proper mappings...")
        
        projects_created = 0
        projects_updated = 0
        
        with open('Projects.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                hs_id = row.get('HS_ID', '').strip()
                if not hs_id or hs_id == 'HS_ID':
                    continue
                
                try:
                    # Get or create project
                    project_data = self.extract_project_data(row)
                    if not project_data:
                        continue
                    
                    project, created = Project.objects.get_or_create(
                        hs_id=hs_id,
                        defaults=project_data
                    )
                    
                    if created:
                        projects_created += 1
                        if projects_created % 10 == 0:
                            self.stdout.write(f"Created {projects_created} projects...")
                    else:
                        # Update existing project
                        for key, value in project_data.items():
                            if value:  # Only update non-empty values
                                setattr(project, key, value)
                        project.save()
                        projects_updated += 1
                
                except Exception as e:
                    self.stdout.write(f"Error processing project {hs_id}: {str(e)}")
        
        self.stdout.write(f"Projects import completed: {projects_created} created, {projects_updated} updated")

    def extract_project_data(self, row):
        """Extract and map project data from CSV row"""
        try:
            # Basic project info
            project_name = row.get('Project Name', '').strip()
            if not project_name:
                return None
            
            # Get city
            city_name = row.get('City', '').strip()
            city = None
            if city_name:
                try:
                    city = LocationCity.objects.get(name=city_name)
                except LocationCity.DoesNotExist:
                    self.stdout.write(f"City not found: {city_name}")
            
            # Get product
            product_name = row.get('HS _Product', '').strip()
            product = None
            if product_name:
                try:
                    product = Product.objects.get(name=product_name)
                except Product.DoesNotExist:
                    self.stdout.write(f"Product not found: {product_name}")
            
            # Get DPM (from APM Name column)
            apm_name = row.get('APM Name', '').strip()
            dpm = None
            if apm_name:
                username = apm_name.lower().replace(' ', '_').replace('&', 'and')[:30]
                try:
                    dpm = User.objects.get(username=username)
                except User.DoesNotExist:
                    self.stdout.write(f"DPM not found: {apm_name}")
            
            # Get account manager (from Sales column)
            sales_name = row.get('Sales', '').strip()
            
            # Get current status
            status_name = row.get('Status', '').strip()
            current_status = None
            if status_name:
                try:
                    current_status = ProjectStatusOption.objects.get(name=status_name)
                except ProjectStatusOption.DoesNotExist:
                    self.stdout.write(f"Status not found: {status_name}")
            
            # Parse latest date for default dates
            latest_date_str = row.get('Latest_Date', '').strip()
            latest_date = self.parse_date(latest_date_str) if latest_date_str else datetime.now().date()
            
            return {
                'project_name': project_name,
                'opportunity_id': row.get('Opp ID', '').strip(),
                'builder_name': row.get('Builder', '').strip(),
                'city': city,
                'product': product,
                'dpm': dpm,
                'account_manager': sales_name,
                'current_status': current_status,
                'quantity': max(1, self.safe_int(row.get('Quantity', '1'))),
                'expected_tat': max(1, self.safe_int(row.get('Expected TAT', '30'))),
                'purchase_date': latest_date,
                'sales_confirmation_date': latest_date
            }
        
        except Exception as e:
            self.stdout.write(f"Error extracting project data: {str(e)}")
            return None

    def import_status_history(self):
        self.stdout.write("Importing status history with latest date tracking...")
        
        history_created = 0
        
        with open('Statuses.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    hs_id = row.get('HS_ID', '').strip()
                    if not hs_id or hs_id == 'HS_ID':
                        continue
                    
                    # Get project
                    try:
                        project = Project.objects.get(hs_id=hs_id)
                    except Project.DoesNotExist:
                        continue
                    
                    # Get status
                    status_name = row.get('Status', '').strip()
                    if not status_name:
                        continue
                    
                    try:
                        status = ProjectStatusOption.objects.get(name=status_name)
                    except ProjectStatusOption.DoesNotExist:
                        continue
                    
                    # Parse date
                    date_str = row.get('Date', '').strip()
                    if not date_str:
                        continue
                    
                    status_date = self.parse_date(date_str)
                    if not status_date:
                        continue
                    
                    # Create status history
                    history, created = ProjectStatusHistory.objects.get_or_create(
                        project=project,
                        status=status,
                        changed_at=status_date,
                        defaults={
                            'category_one_snapshot': status.category_one,
                            'category_two_snapshot': status.category_two,
                            'comments': f'Imported from CSV - Status: {status_name}',
                            'changed_by': project.dpm  # Use project DPM
                        }
                    )
                    
                    if created:
                        history_created += 1
                        if history_created % 50 == 0:
                            self.stdout.write(f"Created {history_created} status history records...")
                
                except Exception as e:
                    self.stdout.write(f"Error processing status history: {str(e)}")
        
        self.stdout.write(f"Status history import completed: {history_created} records created")

    def update_project_metadata(self):
        self.stdout.write("Updating project metadata (latest dates and current status)...")
        
        # Update each project with its latest status and date
        projects = Project.objects.all()
        updated_count = 0
        
        for project in projects:
            # Get latest status history
            latest_history = project.status_history.order_by('-changed_at').first()
            
            if latest_history:
                # Update project's current status
                project.current_status = latest_history.status
                project.save(update_fields=['current_status'])
                updated_count += 1
                
                if updated_count % 20 == 0:
                    self.stdout.write(f"Updated metadata for {updated_count} projects...")
        
        self.stdout.write(f"Project metadata updated for {updated_count} projects")

    def parse_date(self, date_str):
        """Parse date string in various formats"""
        formats = ['%d-%b-%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        self.stdout.write(f"Could not parse date: {date_str}")
        return None

    def safe_int(self, value):
        """Safely convert string to integer"""
        try:
            return int(float(value)) if value.strip() else 0
        except (ValueError, AttributeError):
            return 0

    def safe_decimal(self, value):
        """Safely convert string to decimal"""
        try:
            return Decimal(value) if value.strip() else Decimal('0')
        except (ValueError, AttributeError):
            return Decimal('0') 