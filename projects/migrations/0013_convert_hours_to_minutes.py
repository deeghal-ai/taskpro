# projects/migrations/0013_convert_hours_to_minutes.py

from django.db import migrations

def convert_hours_to_minutes(apps, schema_editor):
    """
    Convert existing hour values to minutes
    """
    ProjectTask = apps.get_model('projects', 'ProjectTask')
    TaskAssignment = apps.get_model('projects', 'TaskAssignment')
    
    # Convert ProjectTask estimated_time from hours to minutes
    for task in ProjectTask.objects.all():
        if task.estimated_time:
            task.estimated_time = task.estimated_time * 60
            task.save()
    
    # Convert TaskAssignment projected_hours from hours to minutes
    for assignment in TaskAssignment.objects.all():
        if assignment.projected_hours:
            assignment.projected_hours = assignment.projected_hours * 60
            assignment.save()

def convert_minutes_to_hours(apps, schema_editor):
    """
    Reverse operation: convert minutes back to hours
    """
    ProjectTask = apps.get_model('projects', 'ProjectTask')
    TaskAssignment = apps.get_model('projects', 'TaskAssignment')
    
    # Convert ProjectTask estimated_time from minutes to hours
    for task in ProjectTask.objects.all():
        if task.estimated_time:
            task.estimated_time = task.estimated_time // 60
            task.save()
    
    # Convert TaskAssignment projected_hours from minutes to hours
    for assignment in TaskAssignment.objects.all():
        if assignment.projected_hours:
            assignment.projected_hours = assignment.projected_hours // 60
            assignment.save()

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_alter_project_delivery_performance_rating_and_more'),  # Updated dependency
    ]

    operations = [
        migrations.RunPython(convert_hours_to_minutes, convert_minutes_to_hours),
    ]