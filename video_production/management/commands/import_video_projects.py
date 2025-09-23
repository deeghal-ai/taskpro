# video_production/management/commands/import_video_projects.py

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from video_production.models import VideoProject, VideoProduct, VideoProjectStatusOption, VideoProjectStatusHistory
from locations.models import City
from accounts.models import User
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Import legacy video projects from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            help='Path to the CSV file containing video project data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the import without saving data (preview mode)'
        )
        parser.add_argument(
            '--create-missing-statuses',
            action='store_true',
            help='Automatically create missing status options'
        )
        parser.add_argument(
            '--default-video-pm',
            type=str,
            help='Username of default VIDEO_PM if not found in data'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        self.dry_run = options['dry_run']
        self.create_missing_statuses = options['create_missing_statuses']
        self.default_video_pm_username = options.get('default_video_pm')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('*** DRY RUN MODE - No data will be saved ***'))
        
        # Verify file exists
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_file}'))
            return
        
        # Load lookup data
        self.load_lookup_data()
        
        # Process CSV
        with transaction.atomic():
            if self.dry_run:
                sid = transaction.savepoint()
            
            try:
                projects_created, histories_created = self.import_projects(csv_file)
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n📊 Import Summary:\n'
                    f'✅ Projects created: {projects_created}\n'
                    f'✅ Status histories created: {histories_created}'
                ))
                
                if self.dry_run:
                    transaction.savepoint_rollback(sid)
                    self.stdout.write(self.style.WARNING('\nDRY RUN: All changes rolled back'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ Import failed: {str(e)}'))
                raise

    def load_lookup_data(self):
        """Load all lookup data into memory for faster processing"""
        self.stdout.write('Loading lookup data...')
        
        # Load cities
        self.cities = {city.name.lower(): city for city in City.objects.select_related('region').all()}
        self.stdout.write(f'  Loaded {len(self.cities)} cities')
        
        # Load video products
        self.products = {product.name.lower(): product for product in VideoProduct.objects.filter(is_active=True)}
        self.stdout.write(f'  Loaded {len(self.products)} video products')
        
        # Load status options
        self.statuses = {status.name.lower(): status for status in VideoProjectStatusOption.objects.filter(is_active=True)}
        self.stdout.write(f'  Loaded {len(self.statuses)} status options')
        
        # Load VIDEO_PM users
        self.video_pms = {
            user.username.lower(): user 
            for user in User.objects.filter(role='VIDEO_PM', is_active=True)
        }
        self.stdout.write(f'  Loaded {len(self.video_pms)} VIDEO_PM users')
        
        # Set default VIDEO_PM
        if self.default_video_pm_username:
            self.default_video_pm = self.video_pms.get(self.default_video_pm_username.lower())
            if not self.default_video_pm:
                raise ValueError(f"Default VIDEO_PM '{self.default_video_pm_username}' not found")
        else:
            self.default_video_pm = list(self.video_pms.values())[0] if self.video_pms else None
            if self.default_video_pm:
                self.stdout.write(f'  Using {self.default_video_pm.username} as default VIDEO_PM')

    def import_projects(self, csv_file):
        """Import projects from CSV"""
        projects_to_create = []
        histories_to_create = []
        errors = []
        row_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                row_count = row_num
                try:
                    # Parse project data
                    project_data = self.parse_project_row(row, row_num)
                    if not project_data:
                        continue
                    
                    # Create project instance (not saved yet)
                    project = VideoProject(**project_data)
                    projects_to_create.append(project)
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    if len(errors) > 10:
                        self.stdout.write(self.style.ERROR(f"Too many errors. Stopping import."))
                        for error in errors:
                            self.stdout.write(self.style.ERROR(f"  {error}"))
                        raise ValueError("Too many import errors")
        
        self.stdout.write(f'\n📋 Parsed {len(projects_to_create)} valid projects from {row_count} rows')
        
        # Display errors if any
        if errors:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Encountered {len(errors)} errors:'))
            for error in errors[:10]:
                self.stdout.write(self.style.WARNING(f'  {error}'))
            if len(errors) > 10:
                self.stdout.write(self.style.WARNING(f'  ... and {len(errors) - 10} more'))
        
        # Create projects one by one to avoid bulk_create issues with status histories
        if projects_to_create and not self.dry_run:
            self.stdout.write('\n💾 Saving projects...')
            
            created_projects = []
            for i, project_data in enumerate(projects_to_create, 1):
                # Manually set hs_id
                project_data.hs_id = f'VP_{i:05d}'
                
                # Set flag to skip automatic status history creation in model.save()
                project_data._skip_status_history = True
                
                # Save project
                project_data.save()
                created_projects.append(project_data)
            
            self.stdout.write(self.style.SUCCESS(f'  Created {len(created_projects)} projects'))
            
            # Create status histories manually with correct logic
            self.stdout.write('\n📝 Creating status histories...')
            histories_count = self.create_status_histories(csv_file, created_projects)
            
            return len(created_projects), histories_count
        
        return len(projects_to_create), 0

    def parse_project_row(self, row, row_num):
        """Parse a single CSV row into project data"""
        # Required fields
        opportunity_id = row.get('opportunity_id', '').strip()
        if not opportunity_id:
            raise ValueError("Missing opportunity_id")
        
        project_name = row.get('project_name', '').strip()
        if not project_name:
            raise ValueError("Missing project_name")
        
        builder_name = row.get('builder_name', '').strip()
        if not builder_name:
            raise ValueError("Missing builder_name")
        
        # City lookup
        city_name = row.get('city_name', '').strip()
        city = self.cities.get(city_name.lower())
        if not city:
            raise ValueError(f"City '{city_name}' not found")
        
        # Product lookup
        product_name = row.get('product_name', '').strip()
        product = self.products.get(product_name.lower())
        if not product:
            raise ValueError(f"Product '{product_name}' not found")
        
        # Status lookup
        status_name = row.get('current_status_name', '').strip()
        current_status = self.statuses.get(status_name.lower())
        if not current_status:
            if self.create_missing_statuses:
                # You could create the status here if needed
                raise ValueError(f"Status '{status_name}' not found")
            else:
                raise ValueError(f"Status '{status_name}' not found")
        
        # Parse dates
        purchase_date = self.parse_date(row.get('purchase_date', ''), 'purchase_date')
        sales_confirmation_date = self.parse_date(row.get('sales_confirmation_date', ''), 'sales_confirmation_date')
        
        # Parse quantity
        try:
            quantity = int(row.get('quantity', 1) or 1)
        except (ValueError, TypeError):
            quantity = 1
        
        # Account manager
        account_manager = row.get('account_manager', '').strip() or 'Unknown'
        
        # Build project data
        project_data = {
            'opportunity_id': opportunity_id,
            'project_type': row.get('project_type', '').strip() if row.get('project_type') else None,
            'project_name': project_name,
            'builder_name': builder_name,
            'city': city,
            'product': product,
            'package_id': row.get('package_id', '').strip() if row.get('package_id') else None,
            'quantity': quantity,
            'purchase_date': purchase_date,
            'sales_confirmation_date': sales_confirmation_date,
            'expected_tat': product.expected_tat,  # Use product default
            'account_manager': account_manager,
            'video_pm': self.default_video_pm,
            'current_status': current_status,
        }
        
        return project_data

    def create_status_histories(self, csv_file, created_projects):
        """Create status histories for the imported projects - exactly 4 types as required"""
        # Create a mapping of opportunity_id to project
        project_map = {p.opportunity_id: p for p in created_projects}
        
        histories_to_create = []
        
        # Get the required status options
        purchase_status = self.statuses.get('purchase date')
        sales_status = self.statuses.get('sale confirmation')  
        project_start_status = self.statuses.get('project start date')
        
        if not purchase_status:
            self.stdout.write(self.style.WARNING('  "Purchase Date" status not found - skipping those histories'))
        if not sales_status:
            self.stdout.write(self.style.WARNING('  "Sale Confirmation" status not found - skipping those histories'))
        if not project_start_status:
            self.stdout.write(self.style.WARNING('  "Project Start Date" status not found - skipping those histories'))
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                opportunity_id = row.get('opportunity_id', '').strip()
                project = project_map.get(opportunity_id)
                
                if not project:
                    continue
                
                try:
                    # 1. ALWAYS create Purchase Date history (required)
                    if purchase_status and row.get('purchase_date', '').strip():
                        purchase_date = self.parse_date(row.get('purchase_date'), 'purchase_date')
                        histories_to_create.append(VideoProjectStatusHistory(
                            project=project,
                            status=purchase_status,
                            changed_by=self.default_video_pm,
                            changed_at=timezone.make_aware(datetime.combine(purchase_date, datetime.min.time())),
                            comments='Purchase Date - imported from legacy data',
                            category_one_snapshot=purchase_status.category_one,
                            category_two_snapshot=purchase_status.category_two
                        ))
                    
                    # 2. ALWAYS create Sales Confirmation history (required)
                    if sales_status and row.get('sales_confirmation_date', '').strip():
                        sales_date = self.parse_date(row.get('sales_confirmation_date'), 'sales_confirmation_date')
                        histories_to_create.append(VideoProjectStatusHistory(
                            project=project,
                            status=sales_status,
                            changed_by=self.default_video_pm,
                            changed_at=timezone.make_aware(datetime.combine(sales_date, datetime.min.time())),
                            comments='Sales Confirmation - imported from legacy data',
                            category_one_snapshot=sales_status.category_one,
                            category_two_snapshot=sales_status.category_two
                        ))
                    
                    # 3. ALWAYS create Current Status history using Latest_date (required)
                    if row.get('Latest_date', '').strip():
                        latest_date = self.parse_date(row.get('Latest_date'), 'Latest_date')
                        histories_to_create.append(VideoProjectStatusHistory(
                            project=project,
                            status=project.current_status,
                            changed_by=self.default_video_pm,
                            changed_at=timezone.make_aware(datetime.combine(latest_date, datetime.min.time())),
                            comments=f'{project.current_status.name} - imported from legacy data',
                            category_one_snapshot=project.current_status.category_one,
                            category_two_snapshot=project.current_status.category_two
                        ))
                    
                    # 4. CONDITIONALLY create Project Start Date history (only if project_start_date exists)
                    if (project_start_status and 
                        row.get('project_start_date', '').strip() and 
                        row.get('project_start_date', '').strip() != ''):
                        start_date = self.parse_date(row.get('project_start_date'), 'project_start_date')
                        histories_to_create.append(VideoProjectStatusHistory(
                            project=project,
                            status=project_start_status,
                            changed_by=self.default_video_pm,
                            changed_at=timezone.make_aware(datetime.combine(start_date, datetime.min.time())),
                            comments='Project Start Date - imported from legacy data',
                            category_one_snapshot=project_start_status.category_one,
                            category_two_snapshot=project_start_status.category_two
                        ))
                        
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Could not create status histories for {opportunity_id}: {e}'))
                    continue
        
        # Bulk create histories
        if histories_to_create:
            VideoProjectStatusHistory.objects.bulk_create(histories_to_create, batch_size=500)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(histories_to_create)} status history entries'))
        
        return len(histories_to_create)

    def parse_date(self, date_str, field_name):
        """Parse date string to date object"""
        if not date_str or date_str.strip() == '':
            raise ValueError(f"Missing {field_name}")
        
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%d-%b-%Y',    # 20-Apr-2023 format (most common in your CSV)
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date '{date_str}' for {field_name}")
