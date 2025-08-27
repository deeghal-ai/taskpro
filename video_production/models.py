from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from accounts.models import User
from locations.models import City
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

class VideoProduct(models.Model):
    """
    Exact mirror of Product model for video production.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the video product"
    )
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Default expected turnaround time in days for this video product"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this video product is available for new projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Video Product'
        verbose_name_plural = 'Video Products'

    def __str__(self):
        return self.name

class VideoProjectStatusOption(models.Model):
    """
    Exact mirror of ProjectStatusOption model for video production.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the status (e.g., 'Sales Confirmation')"
    )
    category_one = models.CharField(
        max_length=100,
        help_text="First level categorization (e.g., 'Pre-Production')"
    )
    category_two = models.CharField(
        max_length=100,
        help_text="Second level categorization (e.g., 'Not Started')"
    )
    order = models.PositiveIntegerField(
        help_text="Sequence number for ordering statuses"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this status is currently available for use"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Video Project Status Option'
        verbose_name_plural = 'Video Project Status Options'

    def __str__(self):
        return f"{self.name} ({self.category_one} - {self.category_two})"

class VideoProject(models.Model):
    """
    Mirror of Project model for video production, without product_subcategory field.
    """
    
    # Basic project information
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    hs_id = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        help_text="Human-readable unique identifier (e.g., VP_00001, VP_00002)"
    )
    opportunity_id = models.CharField(
        max_length=100,
        unique=False,
        help_text="Business opportunity identifier"
    )
    project_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Type of video project (optional)"
    )
    project_name = models.CharField(
        max_length=255,
        help_text="Name of the video project"
    )
    builder_name = models.CharField(
        max_length=255,
        help_text="Name of the builder/client"
    )

    # Location
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='video_projects',
        help_text="City where this video project is located"
    )

    # Product information (NO product_subcategory)
    product = models.ForeignKey(
        VideoProduct,
        on_delete=models.PROTECT,
        related_name='video_projects',
        help_text="The video product being delivered in this project"
    )
    # REMOVED: product_subcategory field
    package_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional package identifier"
    )
    quantity = models.PositiveIntegerField(
        help_text="Quantity of video products for this project"
    )

    # Important dates
    purchase_date = models.DateField(
        help_text="Date when the video project was purchased"
    )
    sales_confirmation_date = models.DateField(
        help_text="Date when sales confirmation was received"
    )
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Expected turnaround time in days (defaults to video product TAT but can be overridden)"
    )

    # Team assignment
    account_manager = models.CharField(
        max_length=255,
        help_text="Name of the account manager responsible for this video project"
    )
    video_pm = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='video_pm_projects',
        help_text="The Video Production Manager assigned to this project"
    )

    # Status tracking
    current_status = models.ForeignKey(
        VideoProjectStatusOption,
        on_delete=models.PROTECT,
        related_name='video_projects',
        help_text="Current status of the video project"
    )

    # Project management fields
    # Note: Video projects don't use project_incharge field - video_pm handles project management
    expected_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected date of video project completion"
    )
    delivery_performance_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text="Delivery performance rating (1-5)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video Project'
        verbose_name_plural = 'Video Projects'
        indexes = [
            models.Index(fields=['opportunity_id']),
        ]

    @property
    def is_delivered(self):
        """
        Check if project is in a 'delivered' state based on category_two field.
        A project is delivered when its current status has category_two = 'Final Delivery'.
        """
        if not self.current_status:
            return False

        return self.current_status.category_two == 'Final Delivery'

    @property
    def delivery_date(self):
        """
        Returns the date of the first status history entry that is considered
        a 'delivered' status (category_two = 'Final Delivery'). Returns None if not found.
        """
        history_entry = self.status_history.filter(
            status__category_two__iexact='Final Delivery'
        ).order_by('changed_at').first()

        return history_entry.changed_at if history_entry else None

    @property
    def is_pipeline(self):
        """
        Check if project is in pipeline state.
        A project is in pipeline if its current status category_two is not 'Final Delivery'.
        """
        if not self.current_status:
            return True  # New projects without status are considered pipeline

        # Pipeline means category_two is not 'Final Delivery'
        return self.current_status.category_two != 'Final Delivery'

    @classmethod
    def generate_hs_id(cls):
        """
        Generates the next available HS_ID in sequence (VP_00001, VP_00002, etc.)
        """
        # Get all video projects with HS_IDs, including the current project being saved
        projects = cls.objects.filter(hs_id__isnull=False).exclude(hs_id='').order_by('hs_id')

        if not projects.exists():
            return 'VP_00001'  # Start with VP_00001 if no projects exist

        # Find the highest HS_ID by parsing all of them
        max_number = 0

        for project in projects:
            if project.hs_id and project.hs_id.startswith('VP_'):
                try:
                    number = int(project.hs_id.split('_')[1])
                    if number > max_number:
                        max_number = number
                except (ValueError, IndexError):
                    # Skip invalid HS_IDs
                    continue

        # Generate next HS_ID
        return f'VP_{max_number + 1:05d}'

    def __str__(self):
        return f"{self.project_name} ({self.opportunity_id})"

    def save(self, *args, **kwargs):
        """
        Custom save method to manage status history and HS_ID generation.
        """
        # ADDED: Check for bulk import flag
        is_bulk_import = kwargs.pop('is_bulk_import', False)
        
        # Check if we should skip status history creation
        skip_status_history = getattr(self, '_skip_status_history', False)

        is_new = self._state.adding
        status_changed = False

        # Track status changes only for existing projects
        if not is_new:
            try:
                old_instance = VideoProject.objects.get(pk=self.pk)
                if old_instance.current_status != self.current_status:
                    status_changed = True
            except VideoProject.DoesNotExist:
                # This case handles an object being created in memory but not yet saved,
                # which shouldn't happen with our current logic but is a good safeguard.
                pass

        # Save the project instance first
        super().save(*args, **kwargs)

        # After saving, create the initial status history, but skip if it's a bulk import or skip flag is set
        if not is_bulk_import and not skip_status_history and (is_new or status_changed):
            # Get the custom status date if provided, otherwise use current datetime
            status_change_date = getattr(self, '_status_change_date', None)
            if status_change_date:
                # Convert date to datetime with current time
                from datetime import datetime, time
                changed_at = timezone.make_aware(datetime.combine(status_change_date, time.min))
            else:
                changed_at = timezone.now()
            
            VideoProjectStatusHistory.objects.create(
                project=self,
                status=self.current_status,
                changed_by=getattr(self, '_current_user', self.video_pm),
                comments=getattr(self, '_status_change_comment', 'Video Project Created'),
                category_one_snapshot=self.current_status.category_one,
                category_two_snapshot=self.current_status.category_two,
                changed_at=changed_at
            )

@receiver(pre_save, sender=VideoProject)
def set_video_project_hs_id(sender, instance, **kwargs):
    """
    Signal receiver to set the HS_ID for a new video project only if it's not already set.
    This is the correct way to handle default value generation.
    """
    if instance._state.adding and not instance.hs_id:
        instance.hs_id = VideoProject.generate_hs_id()

class VideoProjectStatusHistory(models.Model):
    """
    Exact mirror of ProjectStatusHistory model for video production.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    project = models.ForeignKey(
        VideoProject,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text="The video project whose status changed"
    )
    status = models.ForeignKey(
        VideoProjectStatusOption,
        on_delete=models.PROTECT,
        help_text="The status that was set"
    )
    # We store the categories as they were at the time of the status change
    category_one_snapshot = models.CharField(
        max_length=100,
        help_text="Category one value when this status was set"
    )
    category_two_snapshot = models.CharField(
        max_length=100,
        help_text="Category two value when this status was set"
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='video_status_changes',
        help_text="The VIDEO_PM who made this status change"
    )
    changed_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp of the status change"
    )
    comments = models.TextField(
        blank=True,
        help_text="Optional comments about why the status was changed"
    )

    def save(self, *args, **kwargs):
        """
        Override save to capture category snapshots from the status.
        This ensures we maintain historical accuracy of categorizations.
        """
        if self.status and not self.pk:  # Only on creation
            self.category_one_snapshot = self.status.category_one
            self.category_two_snapshot = self.status.category_two
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Video Project Status History'
        verbose_name_plural = 'Video Project Status Histories'

    def __str__(self):
        return f"{self.project.project_name} - {self.status.name} ({self.changed_at})"

class VideoProjectDelivery(models.Model):
    """
    Exact mirror of ProjectDelivery model for video production.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        VideoProject,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    delivery_date = models.DateField(
        help_text="Date when video project reached final delivery status"
    )
    delivery_performance_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text="Delivery performance rating (1-5)"
    )

    # Snapshot data for historical accuracy
    project_name = models.CharField(max_length=255)
    hs_id = models.CharField(max_length=10)
    expected_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField()

    # New field to store the calculated variance
    days_variance_snapshot = models.IntegerField(
        null=True,
        blank=True,
        help_text="Snapshot of days variance at time of delivery"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['project', 'delivery_date']
        indexes = [
            models.Index(fields=['delivery_date']),
        ]
        verbose_name = 'Video Project Delivery'
        verbose_name_plural = 'Video Project Deliveries'

    @property
    def days_variance(self):
        """Calculate days variance dynamically"""
        if self.expected_completion_date and self.actual_completion_date:
            return (self.actual_completion_date - self.expected_completion_date).days
        return self.days_variance_snapshot

    def __str__(self):
        return f"{self.project.project_name} - {self.delivery_date}"
