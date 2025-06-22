from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models import Region, City

class Command(BaseCommand):
    help = 'Populates the City and Region models with a predefined set of data.'

    # Data provided by the user
    CITY_DATA = {
        'South': ['Bangalore', 'Chennai', 'Coimbatore', 'Vijayawada', 'Goa'],
        'West': ['Mumbai', 'Hyderabad', 'Pune', 'Nagpur', 'Nashik', 'Bhopal', 'Thane', 'Visakhapatnam', 'Navi Mumbai'],
        'North': ['Noida', 'Vadodara', 'Kolkata', 'Jaipur', 'Ahmedabad', 'Zirakpur', 'Delhi', 'Chandigarh', 'Surat', 'Indore', 'Gandhinagar', 'Gurgaon', 'Bhubaneswar', 'Lucknow', 'Allahabad', 'Dehradun', 'Mohali'],
        'Unknown': ['Udaipur', 'Rajkot', 'Patna', 'Darbhanga', 'Varanasi', 'Durg']
    }

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting to populate cities and regions...'))
        
        regions_created = 0
        cities_created = 0
        regions_skipped = 0
        cities_skipped = 0

        # Create a default region for cities with no specified region
        unknown_region, created = Region.objects.get_or_create(name='Unknown')
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✅ Created default region: 'Unknown'"))
            regions_created += 1
        else:
            regions_skipped += 1


        for region_name, cities in self.CITY_DATA.items():
            if region_name != 'Unknown':
                region, created = Region.objects.get_or_create(name=region_name)
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Created region: '{region_name}'"))
                    regions_created += 1
                else:
                    regions_skipped += 1
            else:
                region = unknown_region

            for city_name in cities:
                city, created = City.objects.get_or_create(
                    name=city_name,
                    region=region
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"    - Created city: '{city_name}' in '{region.name}'"))
                    cities_created += 1
                else:
                    cities_skipped += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 Population complete! \n'
            f'Regions created: {regions_created}, Skipped: {regions_skipped}\n'
            f'Cities created: {cities_created}, Skipped: {cities_skipped}'
        ))