from django.db import migrations

def generate_hs_id_for_existing_projects(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    current_letter = 'A'
    current_number = 1
    
    for project in Project.objects.order_by('created_at'):
        if not project.hs_id:
            while True:
                hs_id = f'{current_letter}{current_number}'
                if not Project.objects.filter(hs_id=hs_id).exists():
                    project.hs_id = hs_id
                    project.save()
                    break
                
                current_number += 1
                if current_number > 999:
                    current_letter = chr(ord(current_letter) + 1)
                    current_number = 1

def reverse_migration(apps, schema_editor):
    # This allows us to reverse the migration if needed
    Project = apps.get_model('projects', 'Project')
    Project.objects.all().update(hs_id=None)

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0006_project_hs_id'),  # Make sure this matches your previous migration
    ]

    operations = [
        migrations.RunPython(generate_hs_id_for_existing_projects, reverse_migration),
    ]