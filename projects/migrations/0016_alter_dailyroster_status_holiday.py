# Generated by Django 5.2.1 on 2025-05-27 16:41

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0015_dailyroster"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailyroster",
            name="status",
            field=models.CharField(
                choices=[
                    ("PRESENT", "Present"),
                    ("HALF_DAY", "Half Day"),
                    ("LEAVE", "Leave"),
                    ("TEAM_OUTING", "Team Outing"),
                    ("WEEK_OFF", "Week Off"),
                    ("HOLIDAY", "Holiday"),
                ],
                default="PRESENT",
                help_text="Working status for this date",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Holiday",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("date", models.DateField(help_text="Holiday date")),
                ("name", models.CharField(help_text="Holiday name", max_length=200)),
                (
                    "location",
                    models.CharField(
                        default="Gurgaon", help_text="Office location", max_length=100
                    ),
                ),
                ("year", models.PositiveIntegerField(help_text="Year of the holiday")),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this holiday is active"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Holiday",
                "verbose_name_plural": "Holidays",
                "ordering": ["date"],
                "indexes": [
                    models.Index(
                        fields=["date", "location"], name="projects_ho_date_4b1514_idx"
                    ),
                    models.Index(
                        fields=["year", "location"], name="projects_ho_year_2c9a75_idx"
                    ),
                ],
                "unique_together": {("date", "location")},
            },
        ),
    ]
