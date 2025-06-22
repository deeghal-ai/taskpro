# projects/models.py
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

class ProductSubcategory(models.Model):
    """
    A lookup table for product subcategories.

    This model serves as a simple reference list for categorizing projects.
    While independent of products themselves, subcategories help organize
    and classify projects for reporting and analysis purposes.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the subcategory"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this subcategory is available for new projects"
    )
    # Metadata fields - hidden from interface but maintained for system purposes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Subcategory'
        verbose_name_plural = 'Product Subcategories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Represents a product in the system.

    Products are independent entities that define what can be delivered in a project.
    Each product has its own expected turnaround time (TAT) which serves as the
    default duration for projects using this product.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the product"
    )
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Default expected turnaround time in days for this product"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is available for new projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name

class ProjectStatusOption(models.Model):
    """
    Represents a specific status in the project lifecycle with its categorizations.

    Each status entry contains:
    - The status name (like "Sales Confirmation")
    - Its first category (like "Awaiting Data")
    - Its second category (like "Not Started")
    - Its order in the sequence

    This allows for complete flexibility in managing statuses and their
    categorizations through the admin interface.
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
        help_text="First level categorization (e.g., 'Awaiting Data')"
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
        verbose_name = 'Project Status Option'
        verbose_name_plural = 'Project Status Options'

    def __str__(self):
        return f"{self.name} ({self.category_one} - {self.category_two})"


class Project(models.Model):
    """
    The central model representing a project in the system.

    A project represents a specific delivery for a client, linking together
    the product to be delivered, the team responsible, and tracking its
    progression through various status stages.
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
        help_text="Human-readable unique identifier (e.g., A1, A2, B1, etc.)"
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
        help_text="Type of project (optional)"
    )
    project_name = models.CharField(
        max_length=255,
        help_text="Name of the project"
    )
    builder_name = models.CharField(
        max_length=255,
        help_text="Name of the builder/client"
    )

    # Location
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='projects',
        help_text="City where this project is located"
    )

    # Product and category information
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='projects',
        help_text="The product being delivered in this project"
    )
    product_subcategory = models.ForeignKey(
        ProductSubcategory,
        on_delete=models.PROTECT,
        related_name='projects',
        null=True,
        blank=True,
        help_text="Optional subcategory classification for this project"
    )
    package_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional package identifier"
    )
    quantity = models.PositiveIntegerField(
        help_text="Quantity of products for this project"
    )

    # Important dates
    purchase_date = models.DateField(
        help_text="Date when the project was purchased"
    )
    sales_confirmation_date = models.DateField(
        help_text="Date when sales confirmation was received"
    )
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Expected turnaround time in days (defaults to product TAT but can be overridden)"
    )

    # Team assignment
    account_manager = models.CharField(
        max_length=255,
        help_text="Name of the account manager responsible for this project"
    )
    dpm = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='dpm_projects',
        help_text="The Digital Project Manager assigned to this project"
    )

    # Status tracking
    current_status = models.ForeignKey(
        ProjectStatusOption,
        on_delete=models.PROTECT,
        related_name='projects',
        help_text="Current status of the project"
    )

    # Project management fields
    project_incharge = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='incharge_projects',
        null=True,
        blank=True,
        help_text="Team member assigned as project incharge"
    )
    expected_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected date of project completion"
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
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        indexes = [
            models.Index(fields=['opportunity_id']),
        ]

    @property
    def is_delivered(self):
        """
        Check if project is in a 'delivered' or 'terminated' state.
        This now includes Final Delivery, Deemed Consumed, and Opp Dropped.
        """
        if not self.current_status:
            return False

        status_name = self.current_status.name.lower()

        return (
            ('final' in status_name and 'delivery' in status_name) or
            status_name == 'deemed consumed' or
            status_name == 'opp dropped'
        )

    @property
    def delivery_date(self):
        """
        Returns the date of the first status history entry that is considered
        a 'delivered' or 'terminated' status. Returns None if not found.
        """
        history_entry = self.status_history.filter(
            Q(status__name__iexact='Final Delivery') |
            Q(status__name__iexact='Deemed Consumed') |
            Q(status__name__iexact='Opp Dropped')
        ).order_by('changed_at').first()

        return history_entry.changed_at if history_entry else None

    @property
    def is_pipeline(self):
        """
        Check if project is in pipeline state.
        A project is in pipeline if it's not delivered yet.
        Special case: "Approval after deemed consumed" moves it back to pipeline.
        """
        if not self.current_status:
            return True  # New projects without status are considered pipeline

        # Check for special status that moves project back to pipeline
        status_name = self.current_status.name.lower()
        if 'approval' in status_name and 'deemed' in status_name and 'consumed' in status_name:
            return True

        # Otherwise, pipeline means not delivered
        return not self.is_delivered

    @classmethod
    def generate_hs_id(cls):
        """
        Generates the next available HS_ID in sequence (A1, A2,...A999, B1, etc.)
        """
        # Get all projects with HS_IDs, including the current project being saved
        projects = cls.objects.filter(hs_id__isnull=False).exclude(hs_id='').order_by('hs_id')

        if not projects.exists():
            return 'A1'  # Start with A1 if no projects exist

        # Find the highest HS_ID by parsing all of them
        max_letter = 'A'
        max_number = 0

        for project in projects:
            if project.hs_id:
                try:
                    letter = project.hs_id[0]
                    number = int(project.hs_id[1:])

                    # Compare letter first, then number
                    if letter > max_letter or (letter == max_letter and number > max_number):
                        max_letter = letter
                        max_number = number
                except (ValueError, IndexError):
                    # Skip invalid HS_IDs
                    continue

        # Generate next HS_ID
        if max_number >= 999:
            # Move to next letter
            next_letter = chr(ord(max_letter) + 1)
            return f'{next_letter}1'
        else:
            return f'{max_letter}{max_number + 1}'

    def __str__(self):
        return f"{self.project_name} ({self.opportunity_id})"

    def save(self, *args, **kwargs):
        """
        Custom save method to manage status history and HS_ID generation.
        """
        # --- ADDED: Check for bulk import flag ---
        is_bulk_import = kwargs.pop('is_bulk_import', False)

        is_new = self._state.adding
        status_changed = False

        # Track status changes only for existing projects
        if not is_new:
            try:
                old_instance = Project.objects.get(pk=self.pk)
                if old_instance.current_status != self.current_status:
                    status_changed = True
            except Project.DoesNotExist:
                # This case handles an object being created in memory but not yet saved,
                # which shouldn't happen with our current logic but is a good safeguard.
                pass

        # --- REMOVED: Flawed HS_ID generation logic ---

        # Save the project instance first
        super().save(*args, **kwargs)

        # After saving, create the initial status history, but skip if it's a bulk import
        if not is_bulk_import and (is_new or status_changed):
            ProjectStatusHistory.objects.create(
                project=self,
                status=self.current_status,
                changed_by=getattr(self, '_current_user', self.dpm),
                comments=getattr(self, '_status_change_comment', 'Project Created'),
                category_one_snapshot=self.current_status.category_one,
                category_two_snapshot=self.current_status.category_two,
            )

@receiver(pre_save, sender=Project)
def set_project_hs_id(sender, instance, **kwargs):
    """
    Signal receiver to set the HS_ID for a new project only if it's not already set.
    This is the correct way to handle default value generation.
    """
    if instance._state.adding and not instance.hs_id:
        instance.hs_id = Project.generate_hs_id()


class ProjectStatusHistory(models.Model):
    """
    Tracks the complete history of status changes for each project.

    This model maintains a historical record of every status change,
    capturing not just the status itself but also its categories
    at the time of the change. This ensures our historical data
    remains accurate even if status categories are modified later.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text="The project whose status changed"
    )
    status = models.ForeignKey(
        ProjectStatusOption,
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
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='status_changes',
        help_text="The DPM who made this status change"
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
        verbose_name = 'Project Status History'
        verbose_name_plural = 'Project Status Histories'

    def __str__(self):
        return f"{self.project.project_name} - {self.status.name} ({self.changed_at})"


# New model for Product Tasks
class ProductTask(models.Model):
    """
    Represents the available tasks for each product.
    This serves as a lookup table for tasks that can be assigned to projects.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='available_tasks',
        help_text="The product this task belongs to"
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the task"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this task involves"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this task is available for new projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product', 'name']
        unique_together = ['product', 'name']
        verbose_name = 'Product Task'
        verbose_name_plural = 'Product Tasks'

    def __str__(self):
        return self.name


class ProjectTask(models.Model):
    """
    Represents a specific task instance created for a project.
    This is created by the DPM and can have multiple assignments.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    task_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Unique task identifier (e.g., TID_00001)"
    )
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="The project this task belongs to"
    )
    product_task = models.ForeignKey(
        ProductTask,
        on_delete=models.PROTECT,
        related_name='project_tasks',
        help_text="The type of task from product's task list"
    )
    task_type = models.CharField(
        max_length=10,
        choices=[('NEW', 'New'), ('REWORK', 'Rework')],
        help_text="Whether this is a new task or rework"
    )

    estimated_time = models.PositiveIntegerField(
        help_text="Estimated time for task completion (in minutes)"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_tasks',
        help_text="DPM who created this task"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Project Task'
        verbose_name_plural = 'Project Tasks'

    def __str__(self):
        return f"{self.task_id} - {self.project.project_name}"

    def get_formatted_time(self):
        """Convert estimated_time from minutes to HH:MM format"""
        if self.estimated_time is None:
            return '-'
        hours = self.estimated_time // 60
        minutes = self.estimated_time % 60
        return f"{hours:02d}:{minutes:02d}"

    def get_formatted_hours(self):
        """Convert total_projected_hours from minutes to HH:MM format"""
        total_minutes = self.total_projected_hours
        if total_minutes is None or total_minutes == 0:
            return '-'
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def save(self, *args, **kwargs):
        # Generate task_id for new tasks
        if not self.task_id:
            last_task = ProjectTask.objects.order_by('-task_id').first()
            if last_task:
                last_number = int(last_task.task_id.split('_')[1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.task_id = f"TID_{new_number:05d}"

        # Validate the task belongs to project's product
        if self.product_task.product_id != self.project.product_id:
            raise ValidationError("Task must belong to the project's product")

        super().save(*args, **kwargs)

    @property
    def total_projected_hours(self):
        """Returns the sum of projected hours from all assignments"""
        return self.assignments.aggregate(
            total=models.Sum('projected_hours')
        )['total'] or 0



class TaskAssignment(models.Model):
    """
    Represents an assignment of a project task to a team member.
    Each task can be assigned to multiple team members, with each assignment
    tracking its own progress, hours, and quality metrics.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    assignment_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Unique assignment identifier (e.g., ASID_001216)"
    )
    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="The task being assigned"
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='task_assignments',
        help_text="Team member assigned to this task"
    )
    assigned_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When this assignment was created"
    )
    projected_hours = models.PositiveIntegerField(
        help_text="Estimated hours needed for this assignment (in minutes)"
    )
    sub_task = models.TextField(
        help_text="Description of the specific part of the task assigned"
    )
    rework_type = models.CharField(
        max_length=20,
        choices=[
            ('NEW', 'New'),
            ('INTERNAL_REWORK', 'Internal Rework'),
        ],
        null=True,
        blank=True,
        help_text="Type of rework if applicable"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this assignment is visible in team member's dashboard"
    )
    error_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of errors found in this assignment"
    )
    error_description = models.TextField(
        blank=True,
        help_text="Description of errors if any"
    )
    expected_delivery_date = models.DateTimeField(
        help_text="When this assignment is expected to be completed"
    )
    quality_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text="Quality rating for this assignment (1-5)"
    )
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_assignments',
        help_text="DPM who created this assignment"
    )

    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this assignment was marked as completed"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether this assignment is completed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assigned_date']
        verbose_name = 'Task Assignment'
        verbose_name_plural = 'Task Assignments'

    def __str__(self):
        return f"{self.assignment_id} - {self.task.task_id}"

    def get_formatted_hours(self):
        """Convert projected_hours from minutes to HH:MM format"""
        if self.projected_hours is None:
            return '-'
        hours = self.projected_hours // 60
        minutes = self.projected_hours % 60
        return f"{hours:02d}:{minutes:02d}"

    def clean(self):
        super().clean()
        if self.assigned_to and self.assigned_to.role not in ['TEAM_MEMBER', 'DPM']:
            raise ValidationError({
                'assigned_to': 'Tasks can only be assigned to Team Members or DPMs'
            })
    # Add this new method to calculate total working hours
    def get_total_working_hours(self):
        """Calculate total hours worked across all daily totals"""
        total_minutes = self.daily_totals.aggregate(
            total=models.Sum('total_minutes')
        )['total'] or 0

        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def save(self, *args, **kwargs):
        # Generate assignment_id for new assignments
        if not self.assignment_id:
            last_assignment = TaskAssignment.objects.order_by('-assignment_id').first()
            if last_assignment:
                last_number = int(last_assignment.assignment_id.split('_')[1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.assignment_id = f"ASID_{new_number:06d}"

        # Only validate assigned_by role for NEW assignments or when assigned_by is being changed
        if not self.pk or 'assigned_by' in getattr(self, '_changed_fields', []):
            if self.assigned_by and self.assigned_by.role != 'DPM':
                raise ValidationError("Only DPMs can create assignments")

        self.full_clean()  # This will run the validation
        super().save(*args, **kwargs)


class ActiveTimer(models.Model):
    """
    Tracks which team member has an active timer running.
    Only ONE active timer allowed per team member at any time.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        help_text="The assignment being timed"
    )
    team_member = models.OneToOneField(
    'accounts.User',
    on_delete=models.CASCADE,
    help_text="Team member with active timer"
    )
    started_at = models.DateTimeField(
        help_text="When the timer was started"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Active Timer'
        verbose_name_plural = 'Active Timers'

    def __str__(self):
        return f"{self.team_member.username} - {self.assignment.assignment_id}"


class TimeSession(models.Model):
    """
    Individual work sessions (each start/stop cycle creates one session).
    Multiple sessions per day per assignment are allowed.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        related_name='time_sessions',
        help_text="The assignment this session belongs to"
    )
    team_member = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        help_text="Team member who worked this session"
    )
    started_at = models.DateTimeField(
        help_text="When this work session started"
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this work session ended"
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of this session in minutes"
    )
    date_worked = models.DateField(
        help_text="The date this work was performed"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of work done"
    )
    session_type = models.CharField(
        max_length=10,
        choices=[
            ('TIMER', 'Timer Session'),
            ('MANUAL', 'Manual Entry')
        ],
        default='TIMER'
    )
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether this session duration was manually edited"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Time Session'
        verbose_name_plural = 'Time Sessions'

    def __str__(self):
        return f"{self.assignment.assignment_id} - {self.date_worked} - {self.get_formatted_duration()}"

    def get_formatted_duration(self):
        """Convert duration from minutes to HH:MM format"""
        if self.duration_minutes is None:
            return '-'
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return f"{hours:02d}:{minutes:02d}"


class DailyTimeTotal(models.Model):
    """
    Stores the editable daily total for each assignment per team member per day.
    This is what team members can edit directly.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        related_name='daily_totals',
        help_text="The assignment this total belongs to"
    )
    team_member = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        help_text="Team member who worked on this assignment"
    )
    date_worked = models.DateField(
        help_text="The date this total represents"
    )
    total_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total minutes worked on this assignment on this date"
    )
    is_manually_edited = models.BooleanField(
        default=False,
        help_text="Whether this total was manually adjusted by team member"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['assignment', 'team_member', 'date_worked']
        ordering = ['-date_worked']
        verbose_name = 'Daily Time Total'
        verbose_name_plural = 'Daily Time Totals'

    def __str__(self):
        return f"{self.assignment.assignment_id} - {self.team_member.username} - {self.date_worked} - {self.get_formatted_total()}"

    def get_hours(self):
        """Get hours part of total_minutes"""
        return self.total_minutes // 60

    def get_minutes(self):
        """Get minutes part of total_minutes"""
        return self.total_minutes % 60

    def get_formatted_total(self):
        """Convert total from minutes to HH:MM format"""
        hours = self.total_minutes // 60
        minutes = self.total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"


class TimerActionLog(models.Model):
    """
    Audit trail for all timer-related actions.
    This helps track what happened when for debugging and accountability.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        help_text="The assignment this action relates to"
    )
    team_member = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        help_text="Team member who performed this action"
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('START', 'Start Timer'),
            ('STOP', 'Stop Timer'),
            ('MANUAL_ADD', 'Manual Time Added'),
            ('EDIT_SESSION', 'Edited Session Duration'),
            ('COMPLETE', 'Task Completed')
        ]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(
        blank=True,
        help_text="Additional details about this action"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Timer Action Log'
        verbose_name_plural = 'Timer Action Logs'

    def __str__(self):
        return f"{self.assignment.assignment_id} - {self.action} - {self.timestamp}"

# In your models.py - Replace the DailyRoster class with this simplified version

class DailyRoster(models.Model):
    """
    Daily roster tracking for team members.
    SIMPLIFIED: Calculate assignment hours dynamically, no sync needed.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    team_member = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='daily_rosters',
        help_text="Team member this roster entry belongs to"
    )
    date = models.DateField(
        help_text="Date for this roster entry"
    )

    # Working Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PRESENT', 'Present'),
            ('HALF_DAY', 'Half Day'),
            ('LEAVE', 'Leave'),
            ('TEAM_OUTING', 'Team Outing'),
            ('WEEK_OFF', 'Week Off'),
            ('HOLIDAY', 'Holiday')
        ],
        default='PRESENT',
        help_text="Working status for this date"
    )

    # REMOVED: assignment_hours field - calculate dynamically instead

    # Keep only actual user-entered data
    misc_hours = models.PositiveIntegerField(
        default=0,
        help_text="Miscellaneous hours worked (manual entry)"
    )
    misc_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Description of miscellaneous work"
    )

    # Metadata
    is_auto_created = models.BooleanField(
        default=True,
        help_text="Whether this entry was auto-created or manually edited"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes for this day"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['team_member', 'date']
        ordering = ['-date']
        verbose_name = 'Daily Roster'
        verbose_name_plural = 'Daily Rosters'
        indexes = [
            models.Index(fields=['team_member', 'date']),
            models.Index(fields=['date', 'status']),
        ]

    def __str__(self):
        return f"{self.team_member.username} - {self.date} - {self.get_status_display()}"

    @property
    def assignment_hours(self):
        """Calculate assignment hours dynamically from DailyTimeTotal"""
        return DailyTimeTotal.objects.filter(
            team_member=self.team_member,
            date_worked=self.date
        ).aggregate(total=Sum('total_minutes'))['total'] or 0

    @property
    def total_hours(self):
        """Total hours worked (assignment + misc)"""
        return self.assignment_hours + self.misc_hours

    def get_total_hours_formatted(self):
        """Get total hours in HH:MM format"""
        total_minutes = self.total_hours
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def get_assignment_hours_formatted(self):
        """Get assignment hours in HH:MM format"""
        hours = self.assignment_hours // 60
        minutes = self.assignment_hours % 60
        return f"{hours:02d}:{minutes:02d}"

    def get_misc_hours_formatted(self):
        """Get misc hours in HH:MM format"""
        hours = self.misc_hours // 60
        minutes = self.misc_hours % 60
        return f"{hours:02d}:{minutes:02d}"



class Holiday(models.Model):
    """
    Company holidays for automatic roster population.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    date = models.DateField(
        help_text="Holiday date"
    )
    name = models.CharField(
        max_length=200,
        help_text="Holiday name"
    )
    location = models.CharField(
        max_length=100,
        default='Gurgaon',
        help_text="Office location"
    )
    year = models.PositiveIntegerField(
        help_text="Year of the holiday"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this holiday is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['date', 'location']
        ordering = ['date']
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'
        indexes = [
            models.Index(fields=['date', 'location']),
            models.Index(fields=['year', 'location']),
        ]

    def __str__(self):
        return f"{self.name} - {self.date} ({self.location})"



# projects/models.py (additions)

# Removed complex metric models - now using on-demand calculations!
# This simplifies the codebase significantly while maintaining accuracy.


class ProjectDelivery(models.Model):
    """
    Tracks when projects reach final delivery status.
    This is important for historical reporting of delivery performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    project_incharge = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='project_deliveries',
        help_text="The project incharge at time of delivery"
    )
    delivery_date = models.DateField(
        help_text="Date when project reached final delivery status"
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
            models.Index(fields=['project_incharge', 'delivery_date']),
            models.Index(fields=['delivery_date']),
        ]

    @property
    def days_variance(self):
        """Calculate days variance dynamically"""
        if self.expected_completion_date and self.actual_completion_date:
            return (self.actual_completion_date - self.expected_completion_date).days
        return 0