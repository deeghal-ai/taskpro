# Generated by Django 5.2.1 on 2025-05-26 15:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0011_remove_team_leaders"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="delivery_performance_rating",
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text="Delivery performance rating (1-5)",
                max_digits=2,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="expected_completion_date",
            field=models.DateField(
                blank=True, help_text="Expected date of project completion", null=True
            ),
        ),
    ]
