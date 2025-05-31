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
    
    def save(self, *args, **kwargs):
        # If user is DPM, automatically grant staff status
        if self.role == 'DPM':
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)