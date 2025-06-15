from django.core.management.base import BaseCommand
from django.db import models
from projects.models import ProjectStatusOption


class Command(BaseCommand):
    help = 'Add project status options (only creates new ones, preserves existing)'

    def handle(self, *args, **options):
        # List of status options to add: (name, category_one, category_two)
        status_options = [
            ('Sales Confirmation', 'Awaiting Data', 'Not Started'),
            ('Partial Data Received', 'Awaiting Data', 'Not Started'),
            ('Final Data Received', 'Work In Progress', 'Pipeline'),
            ('Project Start Date', 'Work In Progress', 'Pipeline'),
            ('1st Cut Delivery', '1st Cut Delivered', 'Pipeline'),
            ('1st Rework Received', 'Rework', 'Pipeline'),
            ('1st Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('1st Rework Start', 'Rework', 'Pipeline'),
            ('1st Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('2nd Rework Received', 'Rework', 'Pipeline'),
            ('2nd Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('2nd Rework Start', 'Rework', 'Pipeline'),
            ('2nd Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('3nd Rework Received', 'Rework', 'Pipeline'),
            ('3rd Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('3rd Rework Start', 'Rework', 'Pipeline'),
            ('3rd Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('4th Rework Received', 'Rework', 'Pipeline'),
            ('4th Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('4th Rework Start', 'Rework', 'Pipeline'),
            ('4th Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('5th Rework Received', 'Rework', 'Pipeline'),
            ('5th Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('5th Rework Start', 'Rework', 'Pipeline'),
            ('5th Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('Exterior changes done', 'Rework Done, ACC', 'Pipeline'),
            ('L_P Conversion Start', 'Work In Progress', 'Pipeline'),
            ('L_P Conversion End', 'Work In Progress', 'Pipeline'),
            ('L_P Approval', 'Work In Progress', 'Pipeline'),
            ('Photoshoot End', 'Work In Progress', 'Pipeline'),
            ('Photoshoot Start', 'Work In Progress', 'Pipeline'),
            ('Playblast Delivery', 'Work In Progress', 'Pipeline'),
            ('1st Playblast Rework Received', 'Rework', 'Pipeline'),
            ('1st Playblast Rework Clarification', 'Rework', 'Pipeline'),
            ('1st Playblast Rework Start', 'Rework', 'Pipeline'),
            ('1st Playblast Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('2nd Playblast Rework Received', 'Rework', 'Pipeline'),
            ('2nd Playblast Rework Clarification', 'Rework', 'Pipeline'),
            ('2nd Playblast Rework Start', 'Rework', 'Pipeline'),
            ('2nd Playblast Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('3rd Playblast Rework Received', 'Rework', 'Pipeline'),
            ('3rd Playblast Rework Clarification', 'Rework', 'Pipeline'),
            ('3rd Playblast Rework Start', 'Rework', 'Pipeline'),
            ('3rd Playblast Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('Playblast Confirmation', 'Work In Progress', 'Pipeline'),
            ('Render View Delivery', 'Work In Progress', 'Pipeline'),
            ('Confirmation for Final Delivery', 'Work In Progress', 'Pipeline'),
            ('Final Delivery with Watermark', 'Work In Progress', 'Pipeline'),
            ('Final Delivery', 'Final Delivery', 'Final Delivery'),
            ('Deemed Consumed', 'Deemed Consumed', 'Deemed Consumed'),
            ('Hibernate', '', ''),
            ('Nth Delivery', 'Work In Progress', 'Pipeline'),
            ('Nth Confirmation', 'Work In Progress', 'Pipeline'),
            ('1st Nth Rework Received', 'Rework', 'Pipeline'),
            ('1st Nth Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('1st Nth Rework Start', 'Rework', 'Pipeline'),
            ('1st Nth Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('2nd Nth Rework Received', 'Rework', 'Pipeline'),
            ('2nd Nth Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('2nd Nth Rework Start', 'Rework', 'Pipeline'),
            ('2nd Nth Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('3rd Nth Rework Received', 'Rework', 'Pipeline'),
            ('3rd Nth Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('3rd Nth Rework Start', 'Rework', 'Pipeline'),
            ('3rd Nth Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('Tower Modeling Start', 'Work In Progress', 'Pipeline'),
            ('Tower Modeling End', 'Work In Progress', 'Pipeline'),
            ('Tower Modeling Confirmation', 'Work In Progress', 'Pipeline'),
            ('1st Tower Modeling Rework Received', 'Rework', 'Pipeline'),
            ('1st Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('1st Tower Modeling Rework Start', 'Rework', 'Pipeline'),
            ('1st Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('1st Tower Modeling Rework Confirmation', 'Rework', 'Pipeline'),
            ('2nd Tower Modeling Rework Received', 'Rework', 'Pipeline'),
            ('2nd Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('2nd Tower Modeling Rework Start', 'Rework', 'Pipeline'),
            ('2nd Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('2nd Tower Modeling Rework Confirmation', 'Rework', 'Pipeline'),
            ('3rd Tower Modeling Rework Received', 'Rework', 'Pipeline'),
            ('3rd Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('3rd Tower Modeling Rework Start', 'Rework', 'Pipeline'),
            ('3rd Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('3rd Tower Modeling Rework Confirmation', 'Rework', 'Pipeline'),
            ('4th Tower Modeling Rework Received', 'Rework', 'Pipeline'),
            ('4th Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('4th Tower Modeling Rework Start', 'Rework', 'Pipeline'),
            ('4th Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('4th Tower Modeling Rework Confirmation', 'Rework', 'Pipeline'),
            ('5th Tower Modeling Rework Received', 'Rework', 'Pipeline'),
            ('5th Tower Modeling Rework Approval/Clarification', 'Rework', 'Pipeline'),
            ('5th Tower Modeling Rework Start', 'Rework', 'Pipeline'),
            ('5th Tower Modeling Rework End', 'Rework Done, ACC', 'Pipeline'),
            ('5th Tower Modeling Rework Confirmation', 'Rework', 'Pipeline'),
            ('Interior/Amenties', 'Work in Progress', 'Pipeline'),
            ('Purchase Date', '', ''),
            ('On Hold', 'On Hold', 'On Hold'),
            ('Opp Dropped', '', ''),
            ('Approval after Deemed Consume', '', ''),
        ]

        created_count = 0
        skipped_count = 0
        total_existing = ProjectStatusOption.objects.count()
        
        self.stdout.write(f'Found {total_existing} existing status options')
        
        # Get existing status names for quick lookup
        existing_names = set(
            ProjectStatusOption.objects.values_list('name', flat=True)
        )
        
        # Get the highest existing order number
        max_order = ProjectStatusOption.objects.aggregate(
            max_order=models.Max('order')
        )['max_order'] or 0

        for i, (name, category_one, category_two) in enumerate(status_options):
            # Skip empty names
            if not name.strip():
                continue
                
            # Only create if name doesn't exist
            if name in existing_names:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Already exists (skipped): {name}')
                )
            else:
                # Create new status
                ProjectStatusOption.objects.create(
                    name=name,
                    category_one=category_one,
                    category_two=category_two,
                    order=max_order + created_count + 1,
                    is_active=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {name}')
                )

        final_total = ProjectStatusOption.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Summary ===\n'
                f'Existing statuses preserved: {skipped_count}\n'
                f'New statuses created: {created_count}\n'
                f'Total statuses before: {total_existing}\n'
                f'Total statuses after: {final_total}\n'
                f'All existing status options have been preserved!'
            )
        ) 