# projects/management/commands/calculate_metrics.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from accounts.models import User
from projects.models import Project
from projects.services import ReportingService

class Command(BaseCommand):
    help = 'Calculate daily metrics for reporting'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to calculate metrics for (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='Number of days to go back',
        )
    
    def handle(self, *args, **options):
        if options['date']:
            target_date = date.fromisoformat(options['date'])
            dates = [target_date]
        else:
            # Calculate for past N days
            dates = [
                date.today() - timedelta(days=i) 
                for i in range(options['days-back'])
            ]
        
        for calc_date in dates:
            self.stdout.write(f"Calculating metrics for {calc_date}...")
            
            # Calculate for all team members
            team_members = User.objects.filter(role='TEAM_MEMBER')
            for member in team_members:
                ReportingService.calculate_team_member_metrics(member, calc_date)
            
            # Calculate for all active projects
            projects = Project.objects.all()
            for project in projects:
                ReportingService.calculate_project_metrics(project, calc_date)
            
            self.stdout.write(self.style.SUCCESS(f"✓ Completed {calc_date}"))