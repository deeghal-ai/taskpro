import csv
import os
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from projects.models import (
    Project, ProjectStatusHistory, ProjectStatusOption, Product, 
    ProductSubcategory, ProjectDelivery
)
from projects.signals import track_status_changes
from locations.models import City as LocationCity, Region as LocationRegion

User = get_user_model()

class Command(BaseCommand):
    help = 'Import comprehensive project data from CSV files with optimizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--disable-signals', 
            action='store_true',
            help='Disable Django signals during import',
        )

    def handle(self, *args, **options):
        if options['disable_signals']:
            # Disable signals if requested
            from django.db.models import signals
            signals.post_save.receivers = []
            signals.pre_save.receivers = []
            self.stdout.write("Django signals disabled for import")
        
        try:
            self.import_data()
            self.stdout.write(self.style.SUCCESS('Data import completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {str(e)}'))
            raise

    @transaction.atomic
    def import_data(self):
        self.stdout.write("Starting comprehensive data import...")
        
        # Step 1: Import regions and cities
        self.import_regions_and_cities()
        
        # Step 2: Import products
        self.import_products()
        
        # Step 3: Import project statuses with correct mappings
        self.import_project_statuses()
        
        # Step 4: Import users (DPMs)
        self.import_users()
        
        # Step 5: Import projects
        self.import_projects()
        
        # Step 6: Import status history
        self.import_status_history()
        
        # Step 7: Update project metadata
        self.update_project_metadata()

    def import_regions_and_cities(self):
        self.stdout.write("Importing regions and cities...")
        
        # Regional mapping based on your actual data
        regional_mapping = {
            'Bangalore': 'South',
            'Mumbai': 'West',
            'Noida': 'North',
            'Vadodara': 'North',
            'Kolkata': 'North',
            'Jaipur': 'North',
            'Ahmedabad': 'North',
            'Zirakpur': 'North',
            'Hyderabad': 'West',
            'Chennai': 'South',
            'Pune': 'West',
            'Delhi': 'North',
            'Chandigarh': 'North',
            'Nagpur': 'West',
            'Surat': 'North',
            'Indore': 'North',
            'Gandhinagar': 'North',
            'Coimbatore': 'South',
            'Gurgaon': 'North',
            'Nashik': 'West',
            'Bhopal': 'West',
            'Bhubaneswar': 'North',
            'Lucknow': 'North',
            'Allahabad': 'North',
            'Vijayawada': 'South',
            'Thane': 'West',
            'Visakhapatnam': 'West',
            'Goa': 'South',
            'Dehradun': 'North',
            'Mohali': 'North',
            # Cities without region mapping - assign to 'Other'
            'Udaipur': 'Other',
            'Rajkot': 'Other',
            'Patna': 'Other',
            'Darbhanga': 'Other',
            'Varanasi': 'Other',
            'Durg': 'Other',
            'Navi Mumbai': 'Other'
        }
        
        regions_created = 0
        cities_created = 0
        
        # Create regions first
        unique_regions = set(regional_mapping.values())
        for region_name in unique_regions:
            region, created = LocationRegion.objects.get_or_create(
                name=region_name
            )
            if created:
                regions_created += 1
        
        # Create cities
        for city_name, region_name in regional_mapping.items():
            try:
                region = LocationRegion.objects.get(name=region_name)
                city, created = LocationCity.objects.get_or_create(
                    name=city_name,
                    defaults={'region': region}
                )
                if created:
                    cities_created += 1
            except LocationRegion.DoesNotExist:
                self.stdout.write(f"Region not found for city {city_name}: {region_name}")
        
        self.stdout.write(f"Regions and cities import completed: {regions_created} regions, {cities_created} cities created")

    def import_products(self):
        self.stdout.write("Importing products...")
        
        # Products with TAT based on your provided data
        default_products = [
            ('Real_Apartment_Digitour', 21),
            ('Real_Construction_Digitour', 25),
            ('Real_Villa_Digitour', 21),
            ('Virtual_Full_Project_Digitour', 40),
            ('Walkthrough', 72),
            ('Virtual_Apartment_Digitour', 25),
            ('Virtual_Villa_Digitour', 30),
            ('Virtual_Apartment_Dollhouse', 40),
            ('Augmented_Reality', 45),
            ('Short_Video', 15),
            ('Digiplot', 25),
            ('2D_Floor_Plan', 7),
            ('Profile_Video', 30),  # Default TAT for empty values
            ('Digilite', 30),  # Default TAT for empty values
            ('PT_Virtual_Tour', 30),  # Default TAT for empty values
            ('Real_Full_Project_Digitour', 25),
            ('Virtual_Villa_Dollhouse', 45),
            ('RenderViews_StillImages', 21),
            ('Slice_View', 45),
            ('Rework', 30),  # Default TAT for empty values
            ('Custom_Content', 30),  # Default TAT for empty values
            ('3d/2d_Floor_plan', 7),
            ('Real_Location_Digitour', 30),
            ('Additional VO', 12),
            ('Virtual_Villa_Full_Project_Digitour', 40),
            # Additional products found in CSV
            ('Offline Digtour Video Creation', 30)
        ]
        
        products_created = 0
        for name, tat in default_products:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={'expected_tat': tat}
            )
            if created:
                products_created += 1
        
        self.stdout.write(f"Products import completed: {products_created} products created")

    def import_project_statuses(self):
        self.stdout.write("Importing project statuses with correct mappings...")
        
        # Status mappings from your provided data
        status_mappings = [
            ('Sales Confirmation', 'Awaiting Data', 'Not Started', 1),
            ('Partial Data Received', 'Awaiting Data', 'Not Started', 2),
            ('Final Data Received', 'Work In Progress', 'Pipeline', 3),
            ('Project Start Date', 'Work In Progress', 'Pipeline', 4),
            ('1st Cut Delivery', '1st Cut Delivered', 'Pipeline', 5),
            ('1st Rework Received', 'Rework', 'Pipeline', 6),
            ('1st Rework Approval/Clarification', 'Rework', 'Pipeline', 7),
            ('1st Rework Start', 'Rework', 'Pipeline', 8),
            ('1st Rework End', 'Rework Done, ACC', 'Pipeline', 9),
            ('2nd Rework Received', 'Rework', 'Pipeline', 10),
            ('2nd Rework Approval/Clarification', 'Rework', 'Pipeline', 11),
            ('2nd Rework Start', 'Rework', 'Pipeline', 12),
            ('2nd Rework End', 'Rework Done, ACC', 'Pipeline', 13),
            ('3nd Rework Received', 'Rework', 'Pipeline', 14),
            ('3rd Rework Approval/Clarification', 'Rework', 'Pipeline', 15),
            ('3rd Rework Start', 'Rework', 'Pipeline', 16),
            ('3rd Rework End', 'Rework Done, ACC', 'Pipeline', 17),
            ('4th Rework Received', 'Rework', 'Pipeline', 18),
            ('4th Rework Approval/Clarification', 'Rework', 'Pipeline', 19),
            ('4th Rework Start', 'Rework', 'Pipeline', 20),
            ('4th Rework End', 'Rework Done, ACC', 'Pipeline', 21),
            ('5th Rework Received', 'Rework', 'Pipeline', 22),
            ('5th Rework Approval/Clarification', 'Rework', 'Pipeline', 23),
            ('5th Rework Start', 'Rework', 'Pipeline', 24),
            ('5th Rework End', 'Rework Done, ACC', 'Pipeline', 25),
            ('Exterior changes done', 'Rework Done, ACC', 'Pipeline', 26),
            ('L_P Conversion Start', 'Work In Progress', 'Pipeline', 27),
            ('L_P Conversion End', 'Work In Progress', 'Pipeline', 28),
            ('L_P Approval', 'Work In Progress', 'Pipeline', 29),
            ('Photoshoot End', 'Work In Progress', 'Pipeline', 30),
            ('Photoshoot Start', 'Work In Progress', 'Pipeline', 31),
            ('Playblast Delivery', 'Work In Progress', 'Pipeline', 32),
            ('1st Playblast Rework Received', 'Rework', 'Pipeline', 33),
            ('1st Playblast Rework Clarification', 'Rework', 'Pipeline', 34),
            ('1st Playblast Rework Start', 'Rework', 'Pipeline', 35),
            ('1st Playblast Rework End', 'Rework Done, ACC', 'Pipeline', 36),
            ('2nd Playblast Rework Received', 'Rework', 'Pipeline', 37),
            ('2nd Playblast Rework Clarification', 'Rework', 'Pipeline', 38),
            ('2nd Playblast Rework Start', 'Rework', 'Pipeline', 39),
            ('2nd Playblast Rework End', 'Rework Done, ACC', 'Pipeline', 40),
            ('3rd Playblast Rework Received', 'Rework', 'Pipeline', 41),
            ('3rd Playblast Rework Clarification', 'Rework', 'Pipeline', 42),
            ('3rd Playblast Rework Start', 'Rework', 'Pipeline', 43),
            ('3rd Playblast Rework End', 'Rework Done, ACC', 'Pipeline', 44),
            ('Playblast Confirmation', 'Work In Progress', 'Pipeline', 45),
            ('Render View Delivery', 'Work In Progress', 'Pipeline', 46),
            ('Confirmation for Final Delivery', 'Work In Progress', 'Pipeline', 47),
            ('Final Delivery with Watermark', 'Work In Progress', 'Pipeline', 48),
            ('Final Delivery', 'Final Delivery', 'Final Delivery', 49),
            ('Deemed Consumed', 'Deemed Consumed', 'Deemed Consumed', 50),
            ('Nth Delivery', 'Work In Progress', 'Pipeline', 51),
            ('Nth Confirmation', 'Work In Progress', 'Pipeline', 52),
            ('1st Nth Rework Received', 'Rework', 'Pipeline', 53),
            ('1st Nth Rework Approval/Clarification', 'Rework', 'Pipeline', 54),
            ('1st Nth Rework Start', 'Rework', 'Pipeline', 55),
            ('1st Nth Rework End', 'Rework Done, ACC', 'Pipeline', 56),
            ('2nd Nth Rework Received', 'Rework', 'Pipeline', 57),
            ('2nd Nth Rework Approval/Clarification', 'Rework', 'Pipeline', 58),
            ('2nd Nth Rework Start', 'Rework', 'Pipeline', 59),
            ('2nd Nth Rework End', 'Rework Done, ACC', 'Pipeline', 60),
            ('3rd Nth Rework Received', 'Rework', 'Pipeline', 61),
            ('3rd Nth Rework Approval/Clarification', 'Rework', 'Pipeline', 62),
            ('3rd Nth Rework Start', 'Rework', 'Pipeline', 63),
            ('3rd Nth Rework End', 'Rework Done, ACC', 'Pipeline', 64),
            ('Tower Modeling Start', 'Work In Progress', 'Pipeline', 65),
            ('Tower Modeling End', 'Work In Progress', 'Pipeline', 66),
            ('Tower Modeling Confirmation', 'Work In Progress', 'Pipeline', 67),
            ('1st Tower Modeling Rework Received', 'Rework', 'Pipeline', 68),
            ('1st Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline', 69),
            ('1st Tower Modeling Rework Start', 'Rework', 'Pipeline', 70),
            ('1st Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline', 71),
            ('1st Tower Modeling Rework Confirmation', 'Rework', 'Pipeline', 72),
            ('2nd Tower Modeling Rework Received', 'Rework', 'Pipeline', 73),
            ('2nd Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline', 74),
            ('2nd Tower Modeling Rework Start', 'Rework', 'Pipeline', 75),
            ('2nd Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline', 76),
            ('2nd Tower Modeling Rework Confirmation', 'Rework', 'Pipeline', 77),
            ('3rd Tower Modeling Rework Received', 'Rework', 'Pipeline', 78),
            ('3rd Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline', 79),
            ('3rd Tower Modeling Rework Start', 'Rework', 'Pipeline', 80),
            ('3rd Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline', 81),
            ('3rd Tower Modeling Rework Confirmation', 'Rework', 'Pipeline', 82),
            ('4th Tower Modeling Rework Received', 'Rework', 'Pipeline', 83),
            ('4th Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline', 84),
            ('4th Tower Modeling Rework Start', 'Rework', 'Pipeline', 85),
            ('4th Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline', 86),
            ('4th Tower Modeling Rework Confirmation', 'Rework', 'Pipeline', 87),
            ('5th Tower Modeling Rework Received', 'Rework', 'Pipeline', 88),
            ('5th Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline', 89),
            ('5th Tower Modeling Rework Start', 'Rework', 'Pipeline', 90),
            ('5th Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline', 91),
            ('5th Tower Modeling Rework Confirmation', 'Rework', 'Pipeline', 92),
            ('Interior/Amenties', 'Work in Progress', 'Pipeline', 93),
            ('On Hold', 'On Hold', 'On Hold', 94),
        ]
        
        statuses_created = 0
        for name, category_one, category_two, order in status_mappings:
            status, created = ProjectStatusOption.objects.get_or_create(
                name=name,
                defaults={
                    'category_one': category_one,
                    'category_two': category_two,
                    'order': order
                }
            )
            if created:
                statuses_created += 1
        
        self.stdout.write(f"Project statuses import completed: {statuses_created} statuses created")

    def import_users(self):
        self.stdout.write("Importing users (DPMs)...")
        
        # Read unique APM names from CSV
        apm_names = set()
        try:
            with open('Projects.csv', 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Handle multi-line headers - use the key that contains "APM"
                    apm_name = None
                    for key, value in row.items():
                        if 'APM' in key and 'Name' in key:
                            apm_name = value.strip()
                            break
                    
                    if apm_name:
                        apm_names.add(apm_name)
        except FileNotFoundError:
            self.stdout.write("Projects.csv not found, skipping user import")
            return
        
        users_created = 0
        for apm_name in apm_names:
            if not apm_name or apm_name in ['', 'APM Name']:
                continue
                
            # Create username from APM name
            username = apm_name.lower().replace(' ', '_').replace('&', 'and')[:30]
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': apm_name.split()[0] if apm_name.split() else apm_name,
                    'last_name': ' '.join(apm_name.split()[1:]) if len(apm_name.split()) > 1 else '',
                    'email': f"{username}@company.com",
                    'is_active': True,
                    'role': 'DPM'
                }
            )
            if created:
                users_created += 1
        
        self.stdout.write(f"Users import completed: {users_created} users created")

    def import_projects(self):
        self.stdout.write("Importing projects...")
        
        projects_created = 0
        projects_updated = 0
        projects_skipped = 0
        
        try:
            with open('Projects.csv', 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        hs_id = row.get('HS_ID', '').strip()
                        if not hs_id or hs_id == 'HS_ID':
                            continue
                        
                        # Extract project data with flexible column mapping
                        project_data = self.extract_project_data_flexible(row)
                        if not project_data:
                            projects_skipped += 1
                            continue
                        
                        # Skip projects with missing required data
                        if not all([
                            project_data.get('project_name'),
                            project_data.get('city'),
                            project_data.get('product'),
                            project_data.get('dpm'),
                            project_data.get('current_status')
                        ]):
                            self.stdout.write(f"Skipping project {hs_id} - missing required data")
                            projects_skipped += 1
                            continue
                        
                        # Create or update project
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
                        projects_skipped += 1
        
        except FileNotFoundError:
            self.stdout.write("Projects.csv not found")
            return
        
        self.stdout.write(f"Projects import completed: {projects_created} created, {projects_updated} updated, {projects_skipped} skipped")

    def extract_project_data_flexible(self, row):
        """Extract and map project data from CSV row with flexible column mapping"""
        try:
            # Find columns by partial matching since headers might be multi-line
            def find_column_value(row, keywords):
                for key, value in row.items():
                    # Clean up the key by removing line breaks and extra spaces
                    key_clean = key.replace('\n', ' ').replace('\r', ' ').strip()
                    key_lower = key_clean.lower()
                    
                    # Check if any keyword matches
                    for keyword in keywords:
                        if keyword.lower() in key_lower:
                            return value.strip() if value else ''
                return ''
            
            # Debug: Print first row to see what we're working with
            if not hasattr(self, '_debug_printed'):
                self.stdout.write("DEBUG: First row columns:")
                for key, value in row.items():
                    clean_key = key.replace('\n', ' ').replace('\r', ' ').strip()
                    self.stdout.write(f"  '{clean_key}' = '{value[:50]}...' " if len(str(value)) > 50 else f"  '{clean_key}' = '{value}'")
                self._debug_printed = True
            
            # Basic project info - look for "Project" and "Name" in the same column
            project_name = find_column_value(row, ['project name'])
            if not project_name:
                # Try alternative matching
                for key, value in row.items():
                    key_clean = key.replace('\n', ' ').replace('\r', ' ').strip().lower()
                    if 'project' in key_clean and 'name' in key_clean:
                        project_name = value.strip() if value else ''
                        break
            
            if not project_name:
                self.stdout.write(f"DEBUG: No project name found in row")
                return None
            
            self.stdout.write(f"DEBUG: Found project name: '{project_name}'")
            
            # Get city
            city_name = find_column_value(row, ['city'])
            city = None
            if city_name:
                try:
                    city = LocationCity.objects.get(name=city_name)
                    self.stdout.write(f"DEBUG: Found city: {city_name}")
                except LocationCity.DoesNotExist:
                    self.stdout.write(f"City not found: {city_name}")
                    return None
            else:
                self.stdout.write(f"DEBUG: No city found for project {project_name}")
                return None
            
            # Get product
            product_name = find_column_value(row, ['hs _product', 'product'])
            product = None
            if product_name:
                try:
                    product = Product.objects.get(name=product_name)
                    self.stdout.write(f"DEBUG: Found product: {product_name}")
                except Product.DoesNotExist:
                    self.stdout.write(f"Product not found: {product_name}")
                    return None
            else:
                self.stdout.write(f"DEBUG: No product found for project {project_name}")
                return None
            
            # Get DPM (from APM Name column)
            apm_name = find_column_value(row, ['apm name', 'apm'])
            dpm = None
            if apm_name:
                username = apm_name.lower().replace(' ', '_').replace('&', 'and')[:30]
                try:
                    dpm = User.objects.get(username=username)
                    self.stdout.write(f"DEBUG: Found DPM: {apm_name} -> {username}")
                except User.DoesNotExist:
                    self.stdout.write(f"DPM not found: {apm_name} (username: {username})")
                    return None
            else:
                self.stdout.write(f"DEBUG: No APM name found for project {project_name}")
                return None
            
            # Get account manager (from Sales column)
            sales_name = find_column_value(row, ['sales'])
            if not sales_name:
                self.stdout.write(f"DEBUG: No sales name found for project {project_name}")
                return None
            
            self.stdout.write(f"DEBUG: Found sales: {sales_name}")
            
            # Get current status
            status_name = find_column_value(row, ['status'])
            current_status = None
            if status_name:
                try:
                    current_status = ProjectStatusOption.objects.get(name=status_name)
                    self.stdout.write(f"DEBUG: Found status: {status_name}")
                except ProjectStatusOption.DoesNotExist:
                    self.stdout.write(f"Status not found: {status_name}")
                    return None
            else:
                self.stdout.write(f"DEBUG: No status found for project {project_name}")
                return None
            
            # Parse latest date for default dates
            latest_date_str = find_column_value(row, ['latest_date', 'latest date'])
            latest_date = self.parse_date(latest_date_str) if latest_date_str else datetime.now().date()
            
            # Get other fields
            opp_id = find_column_value(row, ['opp id', 'opportunity id'])
            builder_name = find_column_value(row, ['builder'])
            quantity_str = find_column_value(row, ['quantity'])
            tat_str = find_column_value(row, ['expected tat', 'tat'])
            
            self.stdout.write(f"DEBUG: Successfully extracted all data for project {project_name}")
            
            return {
                'project_name': project_name,
                'opportunity_id': opp_id or 'N/A',
                'builder_name': builder_name or 'Unknown Builder',
                'city': city,
                'product': product,
                'dpm': dpm,
                'account_manager': sales_name,
                'current_status': current_status,
                'quantity': max(1, self.safe_int(quantity_str)),
                'expected_tat': max(1, self.safe_int(tat_str) or 30),
                'purchase_date': latest_date,
                'sales_confirmation_date': latest_date
            }
        
        except Exception as e:
            self.stdout.write(f"Error extracting project data: {str(e)}")
            return None

    def import_status_history(self):
        self.stdout.write("Importing status history...")
        
        history_created = 0
        history_skipped = 0
        
        try:
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
                            history_skipped += 1
                            continue
                        
                        # Get status
                        status_name = row.get('Status', '').strip()
                        if not status_name:
                            history_skipped += 1
                            continue
                        
                        try:
                            status = ProjectStatusOption.objects.get(name=status_name)
                        except ProjectStatusOption.DoesNotExist:
                            self.stdout.write(f"Status not found for history: {status_name}")
                            history_skipped += 1
                            continue
                        
                        # Parse date
                        date_str = row.get('Date', '').strip()
                        if not date_str:
                            history_skipped += 1
                            continue
                        
                        status_date = self.parse_date(date_str)
                        if not status_date:
                            history_skipped += 1
                            continue
                        
                        # Convert date to datetime (set time to noon to avoid timezone issues)
                        status_datetime = datetime.combine(status_date, datetime.min.time().replace(hour=12))
                        
                        # Create status history
                        history, created = ProjectStatusHistory.objects.get_or_create(
                            project=project,
                            status=status,
                            changed_at=status_datetime,
                            defaults={
                                'category_one_snapshot': status.category_one,
                                'category_two_snapshot': status.category_two,
                                'comments': f'Imported from CSV - Status: {status_name}',
                                'changed_by': project.dpm
                            }
                        )
                        
                        if created:
                            history_created += 1
                            if history_created % 50 == 0:
                                self.stdout.write(f"Created {history_created} status history records...")
                    
                    except Exception as e:
                        self.stdout.write(f"Error processing status history: {str(e)}")
                        history_skipped += 1
        
        except FileNotFoundError:
            self.stdout.write("Statuses.csv not found")
            return
        
        self.stdout.write(f"Status history import completed: {history_created} records created, {history_skipped} skipped")

    def update_project_metadata(self):
        self.stdout.write("Updating project metadata (latest dates and current status)...")
        
        # Update each project with its latest status and date
        projects = Project.objects.all()
        updated_count = 0
        
        for project in projects:
            # Get latest status history
            latest_history = project.status_history.order_by('-changed_at').first()
            
            if latest_history:
                # Update project's current status to match latest history
                if project.current_status != latest_history.status:
                    project.current_status = latest_history.status
                    project.save(update_fields=['current_status'])
                    updated_count += 1
                    
                    if updated_count % 20 == 0:
                        self.stdout.write(f"Updated metadata for {updated_count} projects...")
        
        self.stdout.write(f"Project metadata updated for {updated_count} projects")

    def parse_date(self, date_str):
        """Parse date string in various formats"""
        formats = ['%d-%b-%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
        
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