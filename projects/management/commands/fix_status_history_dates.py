from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, time
from projects.models import Project, ProjectStatusHistory, ProjectStatusOption
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix status history dates for form-created projects'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no database changes)',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode - no changes will be made'))
        
        # Get status options we need
        purchase_status = ProjectStatusOption.objects.filter(
            name__icontains='purchase',
            is_active=True
        ).first()
        
        sales_status = ProjectStatusOption.objects.filter(
            name__icontains='sales confirmation',
            is_active=True
        ).first()
        
        if not sales_status:
            self.stdout.write(self.style.ERROR('Could not find "Sales Confirmation" status'))
            return
        
        # Find projects that need fixing
        # These are projects where the earliest status history has the same date as created_at
        projects_to_fix = []
        
        for project in Project.objects.all():
            earliest_history = project.status_history.order_by('changed_at').first()
            
            if not earliest_history:
                continue
            
            # Check if the history was likely auto-created (within 1 minute of project creation)
            time_diff = abs(
                (earliest_history.changed_at - project.created_at).total_seconds()
            )
            
            if time_diff < 60:  # Within 1 minute
                projects_to_fix.append(project)
        
        self.stdout.write(f'Found {len(projects_to_fix)} projects to fix')
        
        if not dry_run:
            with transaction.atomic():
                fixed_count = 0
                
                for project in projects_to_fix:
                    try:
                        # Delete incorrect auto-generated histories
                        incorrect_histories = []
                        for history in project.status_history.all():
                            time_diff = abs(
                                (history.changed_at - project.created_at).total_seconds()
                            )
                            if time_diff < 60 and 'Project Created' in history.comments:
                                incorrect_histories.append(history)
                        
                        # Delete them
                        for history in incorrect_histories:
                            self.stdout.write(f'  Deleting incorrect history for {project.hs_id}')
                            history.delete()
                        
                        # Create correct histories
                        # Purchase Date history (if status exists)
                        if purchase_status and project.purchase_date:
                            purchase_datetime = timezone.make_aware(
                                datetime.combine(project.purchase_date, time.min)
                            )
                            ProjectStatusHistory.objects.create(
                                project=project,
                                status=purchase_status,
                                changed_by=project.dpm,
                                comments="Project purchased (fixed)",
                                category_one_snapshot=purchase_status.category_one,
                                category_two_snapshot=purchase_status.category_two,
                                changed_at=purchase_datetime
                            )
                            self.stdout.write(f'  Created purchase history for {project.hs_id}')
                        
                        # Sales Confirmation history
                        sales_datetime = timezone.make_aware(
                            datetime.combine(project.sales_confirmation_date, time.min)
                        )
                        ProjectStatusHistory.objects.create(
                            project=project,
                            status=sales_status,
                            changed_by=project.dpm,
                            comments="Sales confirmed (fixed)",
                            category_one_snapshot=sales_status.category_one,
                            category_two_snapshot=sales_status.category_two,
                            changed_at=sales_datetime
                        )
                        self.stdout.write(f'  Created sales confirmation history for {project.hs_id}')
                        
                        fixed_count += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error fixing project {project.hs_id}: {str(e)}')
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully fixed {fixed_count} projects')
                )
        else:
            # Dry run - just show what would be done
            for project in projects_to_fix[:5]:  # Show first 5 examples
                self.stdout.write(f'\nProject: {project.hs_id} - {project.project_name}')
                self.stdout.write(f'  Purchase Date: {project.purchase_date}')
                self.stdout.write(f'  Sales Confirmation Date: {project.sales_confirmation_date}')
                self.stdout.write(f'  Current histories:')
                for history in project.status_history.all()[:3]:
                    self.stdout.write(f'    - {history.status.name} at {history.changed_at}') 