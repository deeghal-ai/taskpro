# projects/migrations/0011_remove_team_leaders.py

from django.db import migrations, models
import django.db.models.deletion

def remove_tl_data(apps, schema_editor):
    """
    Clean up TL-related data before removing fields
    """
    Project = apps.get_model('projects', 'Project')
    ProjectTeamLeaderHistory = apps.get_model('projects', 'ProjectTeamLeaderHistory')
    
    # Delete all team leader history records
    ProjectTeamLeaderHistory.objects.all().delete()
    
    # Clear team_leader references in projects
    Project.objects.update(team_leader=None)

def reverse_func(apps, schema_editor):
    """
    This migration cannot be reversed as we're deleting data
    """
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_remove_projecttask_quality_label_and_more'),  # Correct dependency
    ]

    operations = [
        # First, clean up the data
        migrations.RunPython(remove_tl_data, reverse_func),
        
        # Then remove the fields and models
        migrations.RemoveField(
            model_name='project',
            name='team_leader',
        ),
        migrations.RemoveField(
            model_name='project',
            name='tl_rating',
        ),
        migrations.RemoveField(
            model_name='project',
            name='tl_rating_date',
        ),
        migrations.RemoveField(
            model_name='project',
            name='tl_rating_comments',
        ),
        migrations.DeleteModel(
            name='ProjectTeamLeaderHistory',
        ),
        
        # Update the help text for created_by in ProjectTask
        migrations.AlterField(
            model_name='projecttask',
            name='created_by',
            field=models.ForeignKey(
                help_text='DPM who created this task',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_tasks',
                to='accounts.User'
            ),
        ),
        
        # Update the help text for assigned_by in TaskAssignment
        migrations.AlterField(
            model_name='taskassignment',
            name='assigned_by',
            field=models.ForeignKey(
                help_text='DPM who created this assignment',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_assignments',
                to='accounts.User'
            ),
        ),
        
        # Update estimated_time field to store minutes instead of hours
        migrations.AlterField(
            model_name='projecttask',
            name='estimated_time',
            field=models.PositiveIntegerField(
                help_text='Estimated time for task completion (in minutes)'
            ),
        ),
        
        # Update projected_hours field to store minutes
        migrations.AlterField(
            model_name='taskassignment',
            name='projected_hours',
            field=models.PositiveIntegerField(
                help_text='Estimated hours needed for this assignment (in minutes)'
            ),
        ),
    ]