from django.db import models
import uuid
from accounts.models import User

class VideoProduct(models.Model):
    """Video product types for outsourced video production"""
    name = models.CharField(max_length=255, unique=True)
    # e.g., "Drone Video", "Corporate Video", "Explainer Video", "Social Media Video"
    typical_cut_rounds = models.PositiveIntegerField(default=3)
    requires_voiceover = models.BooleanField(default=True)
    expected_tat = models.PositiveIntegerField()  # Days for video completion
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class VideoProjectStatusOption(models.Model):
    """Status options for video production projects"""
    name = models.CharField(max_length=100, unique=True)
    # e.g., "Sales Confirmation", "Data Received", "Shoot Done", "1st Cut Delivery", etc.
    category = models.CharField(
        max_length=30,
        choices=[
            ('SALES', 'Sales & Setup'),
            ('PRE_PRODUCTION', 'Pre-Production'),
            ('PRODUCTION', 'Production'),
            ('POST_PRODUCTION', 'Post-Production'),
            ('CUTS', 'Cut Iterations'),
            ('VOICEOVER', 'Voiceover'),
            ('FINAL', 'Final Delivery'),
            ('COMPLETED', 'Completed')
        ],
        default='SALES'
    )
    order = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.name

class VideoProject(models.Model):
    """Main video production project model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hs_id = models.CharField(max_length=50, unique=True)  # Use "VP_" prefix for Video Production
    opportunity_id = models.CharField(max_length=100, unique=True)
    project_name = models.CharField(max_length=255)
    builder_name = models.CharField(max_length=255)
    city = models.ForeignKey('locations.City', on_delete=models.CASCADE)
    
    # Video product information
    video_product = models.ForeignKey(VideoProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    # Video production specific fields
    production_vendor = models.CharField(max_length=255)  # Video agency name
    shoot_location = models.CharField(max_length=255, blank=True)
    shoot_date = models.DateField(null=True, blank=True)
    video_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Timeline
    purchase_date = models.DateField()
    expected_completion_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    # Cut tracking
    current_cut_number = models.PositiveIntegerField(default=0)
    max_cuts_allowed = models.PositiveIntegerField(default=7)
    
    # Voiceover tracking
    voiceover_required = models.BooleanField(default=True)
    voiceover_status = models.CharField(
        max_length=30,
        choices=[
            ('NOT_STARTED', 'Not Started'),
            ('SCRIPT_SHARED', 'Script Shared'),
            ('SCRIPT_APPROVED', 'Script Approved'),
            ('COMPUTERIZED_VO', 'Computerized VO'),
            ('FINAL_RECORDING', 'Final Recording'),
            ('COMPLETED', 'Completed')
        ],
        default='NOT_STARTED'
    )
    
    # Assignment and status
    video_pm = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_projects')
    current_status = models.ForeignKey(VideoProjectStatusOption, on_delete=models.CASCADE)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.hs_id} - {self.project_name}"

class VideoCut(models.Model):
    """Track video cut iterations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(VideoProject, on_delete=models.CASCADE, related_name='cuts')
    cut_number = models.PositiveIntegerField()  # 1, 2, 3, etc.
    status = models.CharField(
        max_length=20,
        choices=[
            ('DELIVERED', 'Delivered'),
            ('REWORK_REQUESTED', 'Rework Requested'),
            ('REWORK_IN_PROGRESS', 'Rework In Progress'),
            ('APPROVED', 'Approved')
        ],
        default='DELIVERED'
    )
    delivered_date = models.DateTimeField(auto_now_add=True)
    feedback_received_date = models.DateTimeField(null=True, blank=True)
    rework_required = models.BooleanField(default=False)
    client_feedback = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['project', 'cut_number']
        ordering = ['cut_number']
    
    def __str__(self):
        return f"{self.project.hs_id} - Cut {self.cut_number}"  # type: ignore

class VoiceoverScript(models.Model):
    """Track voiceover script iterations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(VideoProject, on_delete=models.CASCADE, related_name='voiceover_scripts')
    script_version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('SHARED', 'Shared'),
            ('APPROVED', 'Approved'),
            ('CHANGES_REQUESTED', 'Changes Requested')
        ],
        default='SHARED'
    )
    script_content = models.TextField()
    shared_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['project', 'script_version']
        ordering = ['script_version']
    
    def __str__(self):
        return f"{self.project.hs_id} - VO Script v{self.script_version}"

class VideoProjectStatusHistory(models.Model):
    """Track status changes for video projects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(VideoProject, on_delete=models.CASCADE, related_name='status_history')
    status = models.ForeignKey(VideoProjectStatusOption, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.project.hs_id} - {self.status.name}"  # type: ignore

class VideoProjectDelivery(models.Model):
    """Track delivery performance for video projects"""
    DELIVERY_RATINGS = [
        ('ON_TIME', 'On Time'),
        ('EARLY', 'Early'),
        ('DELAYED', 'Delayed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(VideoProject, on_delete=models.CASCADE, related_name='delivery')
    delivery_performance_rating = models.CharField(max_length=20, choices=DELIVERY_RATINGS)
    delivery_date = models.DateField()
    days_variance = models.IntegerField()  # Positive = late, Negative = early
    total_cuts_delivered = models.PositiveIntegerField()
    voiceover_iterations = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.hs_id} - {self.delivery_performance_rating}"
