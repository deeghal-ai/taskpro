import json
from datetime import datetime
from django.core.management.base import BaseCommand
from projects.models import Holiday


class Command(BaseCommand):
    help = 'Load holidays from JSON data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-data',
            type=str,
            help='JSON string containing holiday data',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing holidays before loading new ones',
        )

    def handle(self, *args, **options):
        # Default holiday data for 2025
        default_holiday_data = {
            "location": "Gurgaon",
            "year": 2025,
            "total_holidays": 17,
            "holidays": [
                {"date": "2025-01-01", "holiday": "New Year"},
                {"date": "2025-01-13", "holiday": "Lohri"},
                {"date": "2025-01-14", "holiday": "Makarsakranti"},
                {"date": "2025-01-26", "holiday": "Republic Day"},
                {"date": "2025-02-26", "holiday": "Mahashivratri"},
                {"date": "2025-03-14", "holiday": "Holi/Dolyatra"},
                {"date": "2025-03-31", "holiday": "Eid Ul Fitr"},
                {"date": "2025-05-01", "holiday": "May Day"},
                {"date": "2025-08-09", "holiday": "Raksha Bandhan"},
                {"date": "2025-08-15", "holiday": "Independence Day"},
                {"date": "2025-08-16", "holiday": "Janmashtami"},
                {"date": "2025-08-27", "holiday": "Ganesh Chaturthi"},
                {"date": "2025-10-02", "holiday": "Gandhi Jayanti"},
                {"date": "2025-10-20", "holiday": "Diwali"},
                {"date": "2025-10-21", "holiday": "Day After Diwali"},
                {"date": "2025-11-05", "holiday": "Guru Nanak Jayanti"},
                {"date": "2025-12-25", "holiday": "Christmas Day"}
            ]
        }
        
        # Use provided JSON data or default
        if options['json_data']:
            try:
                holiday_data = json.loads(options['json_data'])
            except json.JSONDecodeError:
                self.stdout.write(
                    self.style.ERROR('Invalid JSON data provided. Using default holiday data.')
                )
                holiday_data = default_holiday_data
        else:
            holiday_data = default_holiday_data
        
        # Clear existing holidays if requested
        if options['clear_existing']:
            deleted_count = Holiday.objects.filter(
                location=holiday_data['location'],
                year=holiday_data['year']
            ).delete()[0]
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing holidays')
            )
        
        # Load holidays
        created_count = 0
        updated_count = 0
        
        for holiday_item in holiday_data['holidays']:
            holiday_date = datetime.strptime(holiday_item['date'], '%Y-%m-%d').date()
            
            holiday, created = Holiday.objects.get_or_create(
                date=holiday_date,
                location=holiday_data['location'],
                defaults={
                    'name': holiday_item['holiday'],
                    'year': holiday_data['year'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
            else:
                # Update existing holiday
                holiday.name = holiday_item['holiday']
                holiday.year = holiday_data['year']
                holiday.is_active = True
                holiday.save()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded holidays: {created_count} created, {updated_count} updated'
            )
        )