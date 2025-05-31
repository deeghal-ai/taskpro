from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0007_populate_hs_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='hs_id',
            field=models.CharField(
                max_length=10,
                unique=True,
                editable=False,
                help_text='Human-readable unique identifier (e.g., A1, A2, B1, etc.)'
            ),
        ),
    ]