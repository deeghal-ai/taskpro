# projects/management/commands/calculate_metrics.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from accounts.models import User
from projects.models import Project, TaskAssignment
from projects.services import ReportingService

class Command(BaseCommand):
    help = 'Calculate metrics for reporting'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to calculate metrics for (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=30,
            help='Number of days to go back',
        )
        parser.add_argument(
            '--recalculate',
            action='store_true',
            help='Recalculate existing metrics',
        )
    
    def handle(self, *args, **options):
        if options['date']:
            target_date = date.fromisoformat(options['date'])
            dates = [target_date]
        else:
            # Calculate for past N days
            dates = [
                date.today() - timedelta(days=i) 
                for i in range(options['days_back'])
            ]
        
        for calc_date in dates:
            self.stdout.write(f"Calculating metrics for {calc_date}...")
            
            # Calculate for all team members
            team_members = User.objects.filter(role='TEAM_MEMBER')
            for member in team_members:
                try:
                    ReportingService.calculate_team_member_metrics(member, calc_date)
                    self.stdout.write(f"  ✓ {member.username}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ {member.username}: {str(e)}"))
            
            # Track any final deliveries
            from projects.models import ProjectStatusHistory
            deliveries = ProjectStatusHistory.objects.filter(
                changed_at__date=calc_date,
                status__name__icontains='final delivery'
            )
            
            for delivery in deliveries:
                try:
                    ReportingService.track_project_delivery(
                        delivery.project,
                        calc_date
                    )
                    self.stdout.write(f"  ✓ Tracked delivery: {delivery.project.hs_id}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Delivery tracking failed: {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS(f"✓ Completed {calc_date}"))