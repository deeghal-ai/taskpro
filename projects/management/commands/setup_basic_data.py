# projects/management/commands/setup_basic_data.py

from django.core.management.base import BaseCommand
from projects.models import ProductSubcategory, Product, ProjectStatusOption
from locations.models import Region, City

class Command(BaseCommand):
    """
    Django management command to set up initial data required for the project management system.
    
    This command creates all necessary reference data including:
    - Regions and cities
    - Product subcategories
    - Products with their TAT values
    - Project status options with their categorizations
    """
    help = 'Sets up basic data required for the project management system'

    def handle(self, *args, **options):
        """Main command handler that orchestrates the data setup process"""
        self.stdout.write('Starting basic data setup...')

        # Set up all required data in order of dependencies
        self.setup_locations()
        self.setup_subcategories()
        self.setup_products()
        self.setup_status_options()
        
        self.stdout.write(self.style.SUCCESS('Basic data setup completed successfully!'))

    def setup_locations(self):
        """
        Sets up geographical locations including regions and their cities.
        Uses get_or_create to prevent duplicate entries.
        """
        self.stdout.write('Setting up locations...')
        
        region, _ = Region.objects.get_or_create(
            name='North',
            defaults={'name': 'North'}
        )
        
        cities = ['Delhi', 'Gurgaon', 'Noida']
        for city_name in cities:
            City.objects.get_or_create(
                name=city_name,
                region=region,
                defaults={'name': city_name, 'region': region}
            )

    def setup_subcategories(self):
        """
        Sets up product subcategories that help classify projects.
        These subcategories are independent of products.
        """
        self.stdout.write('Setting up product subcategories...')
        
        subcategories = [
            'Highly Custom',
            'Dependent Product',
            'WT Q1',
            'WT Q2',
            'WT Q3',
            'WT Q4'
        ]
        
        for subcat_name in subcategories:
            ProductSubcategory.objects.get_or_create(
                name=subcat_name,
                defaults={
                    'name': subcat_name,
                    'is_active': True
                }
            )

    def setup_products(self):
        """
        Sets up products with their expected turnaround times (TAT).
        Each product includes a default TAT value that can be overridden at the project level.
        """
        self.stdout.write('Setting up products...')
        
        products = [
            {'name': 'Virtual_Full_Project_Digitour', 'expected_tat': 30},
            {'name': 'Walkthrough', 'expected_tat': 45},
            {'name': 'Digiplot', 'expected_tat': 25}
        ]
        
        for product_data in products:
            Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'name': product_data['name'],
                    'expected_tat': product_data['expected_tat'],
                    'is_active': True
                }
            )

    def setup_status_options(self):
        """
        Sets up project status options with their corresponding categories.
        Each status has:
        - A unique name
        - An order number for sequence
        - Two category classifications
        - Active status
        """
        self.stdout.write('Setting up project status options...')
        
        # Define all status options with their categories
        statuses = [
            # (order, name, category_one, category_two)
            (1, 'Sales Confirmation', 'Awaiting Data', 'Not Started'),
            (2, 'Partial Data Received', 'Awaiting Data', 'Not Started'),
            (3, 'Final Data Received', 'Work In Progress', 'Pipeline'),
            (4, 'Project Start Date', 'Work In Progress', 'Pipeline'),
            (5, '1st Cut Delivery', '1st Cut Delivered', 'Pipeline'),
            (6, '1st Rework Received', 'Rework', 'Pipeline'),
            (7, '1st Rework Approval/Clarification', 'Rework', 'Pipeline'),
            (8, '1st Rework Start', 'Rework', 'Pipeline'),
            (9, '1st Rework End', 'Rework Done, ACC', 'Pipeline'),
            (10, '2nd Rework Received', 'Rework', 'Pipeline'),
            (11, '2nd Rework Approval/Clarification', 'Rework', 'Pipeline'),
            (12, '2nd Rework Start', 'Rework', 'Pipeline'),
            (13, '2nd Rework End', 'Rework Done, ACC', 'Pipeline'),
            (14, 'Final Delivery', 'Final Delivery', 'Final Delivery'),
            (15, 'Deemed Consumed', 'Deemed Consumed', 'Deemed Consumed'),
            (16, 'Hibernate', 'Work In Progress', 'Pipeline'),
            (17, 'Nth Delivery', 'Work In Progress', 'Pipeline'),
            (18, 'Nth Confirmation', 'Work In Progress', 'Pipeline')
        ]
        
        # Create each status option
        for order, name, cat_one, cat_two in statuses:
            ProjectStatusOption.objects.get_or_create(
                name=name,
                defaults={
                    'name': name,
                    'order': order,
                    'category_one': cat_one,
                    'category_two': cat_two,
                    'is_active': True
                }
            )