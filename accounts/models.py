#accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    """
    Custom user model to handle user types in our system (DPM, Team Member)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLES = (
        ('DPM', 'Project Manager'),
        ('TEAM_MEMBER', 'Team Member'),
        ('VIDEO_PM', 'Video Production Manager'),
        ('SENIOR_MANAGER', 'Senior Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add these lines to fix the reverse accessor clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
    )

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
    def get_full_name(self):
        """
        Override AbstractUser's get_full_name to provide username as fallback.
        Returns full name if available, otherwise returns username.
        This ensures user names never appear blank in templates.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username
    
    def save(self, *args, **kwargs):
        # If user is DPM or VIDEO_PM, automatically grant staff status and superuser
        if self.role in ['DPM', 'VIDEO_PM']:
            self.is_staff = True
            self.is_superuser = True
        # Senior Manager gets staff status for reporting access but not superuser
        elif self.role == 'SENIOR_MANAGER':
            self.is_staff = True
            self.is_superuser = False
        # Team members get no special privileges
        else:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)