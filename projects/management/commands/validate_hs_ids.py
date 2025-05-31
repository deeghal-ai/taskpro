from django.core.management.base import BaseCommand
from projects.services import ProjectService

class Command(BaseCommand):
    help = 'Validates and optionally repairs the HS_ID sequence in projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Attempt to repair any issues found',
        )

    def handle(self, *args, **options):
        # First validate
        issues = ProjectService.validate_hs_id_sequence()
        
        if not issues:
            self.stdout.write(self.style.SUCCESS('No HS_ID sequence issues found'))
            return
            
        # Print issues
        self.stdout.write(self.style.WARNING('Found the following issues:'))
        for issue in issues:
            self.stdout.write(f"  - {issue}")
            
        # Repair if requested
        if options['repair']:
            self.stdout.write(self.style.WARNING('\nAttempting to repair issues...'))
            success, result = ProjectService.repair_hs_id_sequence()
            
            if success:
                self.stdout.write(self.style.SUCCESS(result))
            else:
                self.stdout.write(self.style.ERROR(result))