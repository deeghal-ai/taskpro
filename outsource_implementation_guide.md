# Comprehensive Video Production Manager Implementation Guide

## Context for AI Assistant

You are helping implement a **Video Production Manager** role in a Django-based project management system called Housing Studio. This is a **continuation of previous work** where the user wants to add video production project management workflow for outsourced video projects using a **NEW DJANGO APP**.

## Current System Overview

### Existing Architecture
- **Django 5.1+ application** with service layer architecture
- **Current Business Domains**: 
  - **3D Visualization** (In-house): DPM + TEAM_MEMBER roles managing 3D renders
  - **Video Production** (Outsourced): NEW domain for live-action video projects
- **Team Structure**: 3 DPMs managing 30 3D visualizers for in-house 3D projects
- **Service Layer Pattern**: Business logic in service classes (ProjectService, etc.)
- **Database**: Uses UUID primary keys, proper foreign key relationships

### Existing Apps Structure
```
taskpro/
├── accounts/          # User management
├── projects/          # In-house 3D visualization management (DPM + TEAM_MEMBER)
├── locations/         # Geographic data
└── video_production/  # NEW APP - Video production project management
```

### Key Models Structure
```python
# accounts/models.py
class User(AbstractUser):
    ROLES = [
        ('DPM', 'Project Manager'),           # 3D Visualization Projects
        ('TEAM_MEMBER', '3D Visualizer'),     # 3D Artists
        # Need to add: ('VIDEO_PM', 'Video Production Manager')
    ]

# projects/models.py - Existing models (DO NOT MODIFY - 3D Visualization Domain)
class Project  # Main in-house 3D visualization project model
class ProjectStatusOption  # 3D visualization status workflow
class Product  # 3D visualization products (Exterior, Interior, Virtual Tour, etc.)
class ProductSubcategory  # 3D complexity levels (Highly Custom, Standard, etc.)
```

## New Requirement: Video Production Manager Role

### Business Requirements
- **New Role**: "VIDEO_PM" (Video Production Manager)
- **NEW DJANGO APP**: Create `video_production` app for complete separation
- **Video Production Workflow**: Live-action video projects outsourced to agencies
- **Different Product Types**: Drone videos, corporate videos, explainer videos, etc.
- **Complex Status Workflow**: Multiple cut iterations, voiceover cycles, watermark previews
- **Vendor Management**: Managing external video production agencies
- **Two Main Views**: Pipeline projects (active) and delivered projects

### Video Production vs 3D Visualization
| Feature | 3D Visualization (In-house) | Video Production (Outsourced) |
|---------|----------------------------|--------------------------------|
| Django App | `projects` app | `video_production` app |
| Product Types | 3D renders, walkthroughs, virtual tours | Drone videos, corporate videos, explainer videos |
| Workflow | Modeling → Rendering → Client Review | Shoot → Multiple Cuts → Voiceover → Final Delivery |
| Team | 30 in-house 3D artists | External video production agencies |
| Status Flow | Simple: Files → Modeling → Rendering → Delivered | Complex: 7+ cut iterations, voiceover cycles |
| Time Tracking | ✅ Detailed artist time tracking | ❌ No time tracking (external vendors) |
| Task Management | ✅ Task assignments to team members | ❌ No task management |
| Vendor Management | ❌ No external vendors | ✅ Video production agencies |

## Video Production Context

### Video Product Types
Our Housing Studio's video production division handles **live-action video content** outsourced to specialized video agencies. Video products include:
- **Drone Video** - Aerial footage of real estate projects
- **Drone Interactive** - Interactive aerial presentations
- **Area Wiki** - Neighborhood and location overview videos
- **Corporate Video** - Company and project promotional content
- **Explainer Video** - Educational content about projects/services
- **Social Media Videos** - Short-form content for social platforms
- **Project Review Video** - Client testimonial and project showcase content

### Video Production Status Workflow
Unlike 3D visualization projects, video production follows a complex multi-stage approval process:

**Complete Status Flow:**
```
Sales Confirmation → Data Received → Shoot Done → 
1st Cut Delivery → 1st Cut Rework → 2nd Cut Delivered → 2nd Cut Rework → 
... (up to 7th Cut) ... → 
Voiceover Script Shared → Voiceover Script Approved → 
Video with Computerized VO Delivered → Changes After Computerized VO → 
Voiceover Approved for Final Recording → Final Video with Watermark Shared → 
Final Delivery
```

### Key Video Production Features
- **Cut Management**: Track multiple video cut iterations (1st, 2nd, 3rd... up to 7th cut)
- **Voiceover Workflow**: Script creation → approval → computerized VO → final recording
- **Watermark Previews**: Client reviews watermarked versions before final delivery
- **Vendor Coordination**: Managing external video production agencies
- **Live Shoot Coordination**: Managing on-location video shoots

## Implementation Plan

### Phase 1: Create New Django App
**Command**: 
```bash
python manage.py startapp video_production
```

**Update settings**:
```python
# pms/settings/base.py
INSTALLED_APPS = [
    # ... existing apps ...
    'video_production',
]
```

### Phase 2: User Role Extension
**File**: `accounts/models.py`
- Add `('VIDEO_PM', 'Video Production Manager')` to ROLES choices
- Update User.save() method to grant staff/superuser privileges to VIDEO_PM role (same as DPM)
- Create migration: `accounts/migrations/0003_add_video_pm_role.py`

### Phase 3: Video Production App Models
**File**: `video_production/models.py`

Create these new models in the video_production app:

```python
from django.db import models
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

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
        return f"{self.project.hs_id} - Cut {self.cut_number}"

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
        return f"{self.project.hs_id} - {self.status.name}"

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
```

**Create migration**: `video_production/migrations/0001_initial.py`

### Phase 4: Video Production App Service Layer
**File**: `video_production/services.py`

Create `VideoProjectService` class:

```python
from django.db import transaction
from django.utils import timezone
from .models import VideoProject, VideoProjectStatusOption, VideoProjectStatusHistory, VideoCut, VoiceoverScript, VideoProjectDelivery

class VideoProjectService:
    @staticmethod
    def create_video_project(project_data, user):
        """Create new video production project with validation"""
        
    @staticmethod
    def get_video_project(project_id):
        """Get single video project"""
        
    @staticmethod
    def get_video_project_details(project_id):
        """Get project with full details including cuts and voiceover history"""
        
    @staticmethod
    def update_video_project_status(project_id, status_id, comments, user):
        """Update project status and create history record"""
        
    @staticmethod
    def submit_video_cut(project_id, cut_number, user):
        """Submit a video cut for client review"""
        
    @staticmethod
    def request_cut_rework(project_id, cut_number, feedback, user):
        """Request rework on a video cut"""
        
    @staticmethod
    def submit_voiceover_script(project_id, script_content, user):
        """Submit voiceover script for approval"""
        
    @staticmethod
    def approve_voiceover_script(project_id, script_version, user):
        """Approve voiceover script"""
        
    @staticmethod
    def get_video_project_list(video_pm, filters=None):
        """Get filtered list of projects for video PM"""
        
    @staticmethod
    def get_video_filter_options():
        """Get filter options for project list UI"""
        
    @staticmethod
    def track_video_project_delivery(project_id):
        """Track delivery performance when project is completed"""
```

### Phase 5: Video Production App Forms
**File**: `video_production/forms.py`

Create forms for the video_production app:

```python
from django import forms
from .models import VideoProject, VideoProjectStatusOption, VideoCut, VoiceoverScript

class VideoProjectCreateForm(forms.ModelForm):
    """Form for creating video production projects"""
    class Meta:
        model = VideoProject
        fields = [
            'opportunity_id', 'project_name', 'builder_name', 'city',
            'video_product', 'quantity', 'production_vendor',
            'shoot_location', 'shoot_date', 'video_duration_minutes',
            'purchase_date', 'expected_completion_date',
            'voiceover_required', 'max_cuts_allowed'
        ]

class VideoProjectStatusUpdateForm(forms.Form):
    """Form for updating video project status"""
    status = forms.ModelChoiceField(queryset=VideoProjectStatusOption.objects.filter(is_active=True))
    comments = forms.CharField(widget=forms.Textarea, required=False)

class VideoCutSubmissionForm(forms.ModelForm):
    """Form for submitting video cuts"""
    class Meta:
        model = VideoCut
        fields = ['cut_number']

class VoiceoverScriptForm(forms.ModelForm):
    """Form for submitting voiceover scripts"""
    class Meta:
        model = VoiceoverScript
        fields = ['script_content']

class VideoProjectFilterForm(forms.Form):
    """Form for filtering video project lists"""
    status = forms.ModelChoiceField(queryset=VideoProjectStatusOption.objects.filter(is_active=True), required=False)
    vendor = forms.CharField(max_length=255, required=False)
    city = forms.ModelChoiceField(queryset=None, required=False)  # Set in __init__
    video_product = forms.ModelChoiceField(queryset=None, required=False)  # Set in __init__
```

### Phase 6: Video Production App Views
**File**: `video_production/views.py`

Create views for the video_production app:

```python
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from .models import VideoProject
from .services import VideoProjectService
from .forms import VideoProjectCreateForm, VideoProjectStatusUpdateForm, VideoProjectFilterForm

def ensure_is_video_pm(user):
    """Helper function to check VIDEO_PM role"""
    if user.role != 'VIDEO_PM':
        raise PermissionDenied("Access denied. Video Production Manager role required.")

@login_required
def video_create_project(request):
    """Create new video production project - VIDEO_PM only"""

@login_required
def video_project_detail(request, project_id):
    """View video project details with cuts and voiceover history"""

@login_required
def video_update_project_status(request, project_id):
    """Update project status - supports AJAX"""

@login_required
def video_project_list(request):
    """List pipeline (active) video projects"""

@login_required
def video_delivered_projects(request):
    """List delivered video projects"""

@login_required
def video_submit_cut(request, project_id):
    """Submit video cut for client review"""

@login_required
def video_submit_voiceover_script(request, project_id):
    """Submit voiceover script for approval"""
```

### Phase 7: Video Production App URLs
**File**: `video_production/urls.py`

```python
from django.urls import path
from . import views

app_name = 'video_production'

urlpatterns = [
    path('', views.video_project_list, name='project_list'),
    path('delivered/', views.video_delivered_projects, name='delivered_projects'),
    path('create/', views.video_create_project, name='create_project'),
    path('<uuid:project_id>/', views.video_project_detail, name='project_detail'),
    path('<uuid:project_id>/update-status/', views.video_update_project_status, name='update_status'),
    path('<uuid:project_id>/submit-cut/', views.video_submit_cut, name='submit_cut'),
    path('<uuid:project_id>/submit-voiceover/', views.video_submit_voiceover_script, name='submit_voiceover'),
]
```

**File**: `pms/urls.py`
```python
# Add to existing urlpatterns
path('video-production/', include('video_production.urls')),
```

### Phase 8: Video Production App Templates
Create directory: `video_production/templates/video_production/`

Templates to create:
- `video_create_project.html`
- `video_project_detail.html`
- `video_project_list.html`
- `video_delivered_projects.html`

### Phase 9: Video Production App Admin
**File**: `video_production/admin.py`

```python
from django.contrib import admin
from .models import VideoProduct, VideoProject, VideoProjectStatusOption, VideoCut, VoiceoverScript, VideoProjectStatusHistory, VideoProjectDelivery

@admin.register(VideoProduct)
class VideoProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'typical_cut_rounds', 'requires_voiceover', 'expected_tat', 'is_active']
    list_filter = ['requires_voiceover', 'is_active']

@admin.register(VideoProjectStatusOption)
class VideoProjectStatusOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']

@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = ['hs_id', 'project_name', 'video_pm', 'current_status', 'current_cut_number', 'created_at']
    list_filter = ['current_status', 'video_pm', 'city', 'video_product']
    search_fields = ['hs_id', 'project_name', 'builder_name']
```

### Phase 10: Navigation Updates
**File**: `templates/base.html`
Add navigation links for VIDEO_PM role

## App Structure After Implementation

```
video_production/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py
├── models.py
├── services.py
├── views.py
├── urls.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── templates/
│   └── video_production/
│       ├── video_create_project.html
│       ├── video_project_detail.html
│       ├── video_project_list.html
│       └── video_delivered_projects.html
└── tests.py
```

## Implementation Guidelines

### Code Patterns to Follow
1. **New Django app** for complete separation from existing 3D visualization functionality
2. **Reference existing models** (City) via foreign keys where appropriate
3. **Use service layer** for all business logic
4. **Maintain consistent naming** with existing codebase
5. **Follow UUID primary key pattern** for new models
6. **Use proper foreign key relationships** with related_name
7. **Implement proper validation** in forms and services
8. **Add role-based access control** to all views
9. **Support both regular and AJAX requests** where appropriate

### Database Design Principles
- **Separate app with separate models** for clean separation
- **Video-specific models** for cuts, voiceover scripts, vendor management
- **Similar field structures** to maintain consistency with existing project models
- **Proper indexing** on frequently queried fields
- **Cascade deletion** where appropriate
- **Audit fields** (created_at, updated_at) on all models

### Security Considerations
- **Role-based access control** for all video production views
- **Permission checking** in service layer methods
- **Input validation** in forms and services
- **CSRF protection** on all forms
- **Proper error handling** for unauthorized access

## Testing Strategy
1. **Create test data** for video projects with different cut iterations
2. **Test role permissions** thoroughly
3. **Verify no impact** on existing DPM/TEAM_MEMBER functionality
4. **Test database migrations** on copy of production data
5. **Test all CRUD operations** for video projects
6. **Test cut submission and voiceover workflows**

## Deployment Steps
1. **Create video_production app**: `python manage.py startapp video_production`
2. **Add to INSTALLED_APPS** in settings
3. **Create and run migrations** in correct order
4. **Test on staging environment** first
5. **Verify existing functionality** remains intact
6. **Create initial video status options** via admin or management command
7. **Create initial video products** (Drone Video, Corporate Video, etc.)
8. **Train users** on new video production workflow

## Key Success Criteria
- ✅ New `video_production` Django app created with complete separation
- ✅ VIDEO_PM role can create and manage video production projects
- ✅ Complex video workflow with cut iterations and voiceover cycles
- ✅ Existing DPM and TEAM_MEMBER functionality unchanged
- ✅ Clean separation between 3D visualization and video production projects
- ✅ Proper role-based access control
- ✅ Consistent UI/UX with existing application
- ✅ Unified reporting includes both 3D and video projects

## Next Steps for AI Assistant
1. **Start with Phase 1** (Create new Django app)
2. **Add to INSTALLED_APPS** in settings
3. **Proceed systematically** through each phase
4. **Test after each phase** to ensure no breaking changes
5. **Follow existing code patterns** and architecture
6. **Ask for clarification** if business requirements are unclear

---

**Important**: This uses a **NEW DJANGO APP** called `video_production` for complete separation from the existing `projects` app (which handles 3D visualization). The video production domain has fundamentally different workflows, status options, and business logic compared to 3D visualization projects. 