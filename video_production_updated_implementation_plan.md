# Video Production Implementation Plan
## Refactoring Existing Video Production App to Mirror Projects App

### Current State & Context

#### Git Branch Structure
- **Main Branch**: Currently deployed in production on PythonAnywhere
  - Contains the stable `projects` app for 3D visualization projects
  - No video_production code exists here
- **Feature Branch**: `feature/video-production-manager` 
  - Contains the already-implemented `video_production` app
  - Has complex models (VideoCut, VoiceoverScript) that need removal
  - Models need modification to exactly mirror projects app
  - Will be merged to main after successful refactoring

#### What Already Exists in Feature Branch
- ✅ `video_production` app created
- ✅ Models created (but overly complex with cuts/voiceover tracking)
- ✅ Added to INSTALLED_APPS in settings
- ✅ URLs configured in pms/urls.py
- ✅ Views and forms created (but need simplification)
- ✅ Templates created (need modification)
- ✅ VIDEO_PM role added to accounts/models.py

#### What Needs to Change
1. **DELETE** unnecessary models: VideoCut, VoiceoverScript
2. **MODIFY** existing models to exactly mirror projects app
3. **REMOVE** video-specific fields (shoot_location, shoot_date, etc.)
4. **UPDATE** forms to remove cut/voiceover functionality
5. **SIMPLIFY** views to match projects app patterns
6. **UPDATE** templates to remove complex features

### CRITICAL REQUIREMENTS
- **DO NOT** add any fields that aren't in the projects app
- **DO NOT** modify any existing projects app code in main branch
- **DO NOT** use choice fields where projects app uses CharField
- **MUST** use UUID primary keys exactly like projects app
- **MUST** mirror field types, validators, and help_text exactly
- **MUST** maintain same field naming conventions
- **MUST** handle migrations carefully due to existing model structure

---

## Phase 1: Model Structure Comparison

### Projects App Models → Video Production App Models

| Projects App Model | Video Production App Model | Differences |
|-------------------|---------------------------|-------------|
| Product | VideoProduct | None - exact mirror |
| ProductSubcategory | ❌ Not Needed | Video projects don't use subcategories |
| ProjectStatusOption | VideoProjectStatusOption | None - exact mirror |
| Project | VideoProject | Remove: product_subcategory field |
| ProjectStatusHistory | VideoProjectStatusHistory | None - exact mirror |
| ProjectDelivery | VideoProjectDelivery | None - exact mirror |
| Task-related models | ❌ Not Needed | No task management in video production |

---

## Phase 2: Detailed Model Specifications

### 2.1 VideoProduct Model
```python
class VideoProduct(models.Model):
    """Exact mirror of Product model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Name of the video product")
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Default expected turnaround time in days for this video product"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this video product is available for new projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Video Product'
        verbose_name_plural = 'Video Products'
```

### 2.2 VideoProjectStatusOption Model
```python
class VideoProjectStatusOption(models.Model):
    """Exact mirror of ProjectStatusOption model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Name of the status (e.g., 'Sales Confirmation')")
    category_one = models.CharField(max_length=100, help_text="First level categorization (e.g., 'Pre-Production')")
    category_two = models.CharField(max_length=100, help_text="Second level categorization (e.g., 'Not Started')")
    order = models.PositiveIntegerField(help_text="Sequence number for ordering statuses")
    is_active = models.BooleanField(default=True, help_text="Whether this status is currently available for use")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Video Project Status Option'
        verbose_name_plural = 'Video Project Status Options'
```

### 2.3 VideoProject Model
```python
class VideoProject(models.Model):
    """Mirror of Project model, without product_subcategory field"""
    # Basic project information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hs_id = models.CharField(
        max_length=10, unique=True, editable=False,
        help_text="Human-readable unique identifier (e.g., VP_00001, VP_00002)"
    )
    opportunity_id = models.CharField(max_length=100, unique=False, help_text="Business opportunity identifier")
    project_type = models.CharField(max_length=100, blank=True, null=True, help_text="Type of video project (optional)")
    project_name = models.CharField(max_length=255, help_text="Name of the video project")
    builder_name = models.CharField(max_length=255, help_text="Name of the builder/client")
    
    # Location
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='video_projects', help_text="City where this video project is located")
    
    # Product information (NO product_subcategory)
    product = models.ForeignKey(VideoProduct, on_delete=models.PROTECT, related_name='video_projects', help_text="The video product being delivered in this project")
    # REMOVED: product_subcategory field
    package_id = models.CharField(max_length=100, blank=True, null=True, help_text="Optional package identifier")
    quantity = models.PositiveIntegerField(help_text="Quantity of video products for this project")
    
    # Important dates
    purchase_date = models.DateField(help_text="Date when the video project was purchased")
    sales_confirmation_date = models.DateField(help_text="Date when sales confirmation was received")
    expected_tat = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Expected turnaround time in days (defaults to video product TAT but can be overridden)"
    )
    
    # Team assignment
    account_manager = models.CharField(max_length=255, help_text="Name of the account manager responsible for this video project")
    dpm = models.ForeignKey(User, on_delete=models.PROTECT, related_name='video_dpm_projects', help_text="The Video Production Manager assigned to this project")
    
    # Status tracking
    current_status = models.ForeignKey(VideoProjectStatusOption, on_delete=models.PROTECT, related_name='video_projects', help_text="Current status of the video project")
    
    # Project management fields
    project_incharge = models.ForeignKey(User, on_delete=models.PROTECT, related_name='video_incharge_projects', null=True, blank=True, help_text="Team member assigned as video project incharge")
    expected_completion_date = models.DateField(null=True, blank=True, help_text="Expected date of video project completion")
    delivery_performance_rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Delivery performance rating (1-5)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2.4 VideoProjectStatusHistory Model
```python
class VideoProjectStatusHistory(models.Model):
    """Exact mirror of ProjectStatusHistory model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(VideoProject, on_delete=models.CASCADE, related_name='status_history', help_text="The video project whose status changed")
    status = models.ForeignKey(VideoProjectStatusOption, on_delete=models.PROTECT, help_text="The status that was set")
    category_one_snapshot = models.CharField(max_length=100, help_text="Category one value when this status was set")
    category_two_snapshot = models.CharField(max_length=100, help_text="Category two value when this status was set")
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='video_status_changes', help_text="The VIDEO_PM who made this status change")
    changed_at = models.DateTimeField(default=timezone.now, help_text="Timestamp of the status change")
    comments = models.TextField(blank=True, help_text="Optional comments about why the status was changed")
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Video Project Status History'
        verbose_name_plural = 'Video Project Status Histories'
```

### 2.5 VideoProjectDelivery Model
```python
class VideoProjectDelivery(models.Model):
    """Exact mirror of ProjectDelivery model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(VideoProject, on_delete=models.CASCADE, related_name='deliveries')
    project_incharge = models.ForeignKey(User, on_delete=models.PROTECT, related_name='video_project_deliveries', help_text="The project incharge at time of delivery")
    delivery_date = models.DateField(help_text="Date when video project reached final delivery status")
    delivery_performance_rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Delivery performance rating (1-5)"
    )
    
    # Snapshot data for historical accuracy
    project_name = models.CharField(max_length=255)
    hs_id = models.CharField(max_length=10)
    expected_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField()
    days_variance_snapshot = models.IntegerField(null=True, blank=True, help_text="Snapshot of days variance at time of delivery")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'delivery_date']
        indexes = [
            models.Index(fields=['project_incharge', 'delivery_date']),
            models.Index(fields=['delivery_date']),
        ]
```

---

## Phase 3: Migration Strategy

### 3.1 Initial Migration Order
1. Create `video_production` app
2. Add to INSTALLED_APPS
3. Create models in exact order:
   - VideoProduct
   - VideoProjectStatusOption
   - VideoProject
   - VideoProjectStatusHistory
   - VideoProjectDelivery

### 3.2 Migration Commands
```bash
# Step 1: Create the app
python manage.py startapp video_production

# Step 2: After adding models, create migrations
python manage.py makemigrations video_production

# Step 3: Review migrations to ensure correctness
python manage.py showmigrations video_production

# Step 4: Apply migrations
python manage.py migrate video_production
```

### 3.3 Data Migration for Initial Status Options
Create a data migration to add initial video project status options:
```python
# video_production/migrations/0002_initial_status_options.py
def create_initial_statuses(apps, schema_editor):
    VideoProjectStatusOption = apps.get_model('video_production', 'VideoProjectStatusOption')
    
    statuses = [
        ('Sales Confirmation', 'Pre-Production', 'Not Started', 1),
        ('Data Received', 'Pre-Production', 'In Progress', 2),
        ('Shoot Scheduled', 'Production', 'Not Started', 3),
        ('Shoot Done', 'Production', 'In Progress', 4),
        ('Post-Production', 'Post-Production', 'In Progress', 5),
        ('Client Review', 'Post-Production', 'Review', 6),
        ('Final Delivery', 'Delivery', 'Final Delivery', 7),
    ]
    
    for name, cat1, cat2, order in statuses:
        VideoProjectStatusOption.objects.create(
            name=name,
            category_one=cat1,
            category_two=cat2,
            order=order,
            is_active=True
        )
```

---

## Phase 4: Service Layer Implementation

### 4.1 VideoProjectService
Mirror the ProjectService exactly, adapting for video projects:
- `create_video_project()` - Same logic as `create_project()` but with VP_ prefix
- `get_video_project()` - Same as `get_project()`
- `get_video_project_details()` - Same as `get_project_details()`
- `update_video_project_status()` - Same as `update_project_status()`
- `get_video_project_list()` - Same as `get_project_list()`

Key differences:
- Use VP_ prefix for hs_id generation (VP_00001, VP_00002, etc.)
- Reference VideoProject models instead of Project models
- No task-related methods

---

## Phase 5: Forms Implementation

### 5.1 VideoProjectCreateForm
Mirror ProjectCreateForm exactly, but:
- Remove product_subcategory field
- Use VideoProduct and VideoProjectStatusOption
- Same validation logic

### 5.2 VideoProjectStatusUpdateForm
Exact mirror of ProjectStatusUpdateForm

### 5.3 VideoProjectFilterForm
Mirror ProjectFilterForm but use video models

---

## Phase 6: Views Implementation

### Required Views (Mirror of projects app)
1. `video_project_list` - Same as `project_list`
2. `video_create_project` - Same as `create_project`
3. `video_project_detail` - Same as `project_detail`
4. `video_update_project_status` - Same as `update_project_status`
5. `video_delivered_projects` - Same as `delivered_projects`

### Views NOT Needed (Task-related)
- No task dashboard
- No assignment views
- No timer views
- No roster views

---

## Phase 7: Templates Implementation

### Templates Structure
```
video_production/templates/video_production/
├── video_project_list.html      # Mirror of project_list.html
├── video_create_project.html    # Mirror of create_project.html
├── video_project_detail.html    # Mirror of project_detail.html
└── video_delivered_projects.html # Mirror of delivered_projects.html
```

### Template Differences
- Remove product_subcategory field from forms
- Use video_production URLs namespace
- Purple color scheme (#9b59b6) instead of blue for differentiation

---

## Phase 8: URL Configuration

### video_production/urls.py
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
]
```

### pms/urls.py Addition
```python
path('video-production/', include('video_production.urls')),
```

---

## Phase 9: Admin Configuration

Mirror the projects app admin configuration:
- VideoProductAdmin
- VideoProjectStatusOptionAdmin
- VideoProjectAdmin
- VideoProjectStatusHistoryAdmin
- VideoProjectDeliveryAdmin

---

## Phase 10: Testing & Validation

### 10.1 Pre-deployment Checklist
- [ ] All models match projects app structure (minus excluded models)
- [ ] UUID primary keys on all models
- [ ] No choice fields where projects uses CharField
- [ ] No extra fields added
- [ ] VP_ prefix for hs_id working
- [ ] Forms validation matching projects app
- [ ] Status history created on project save
- [ ] AJAX status updates working
- [ ] Templates rendering correctly

### 10.2 Test Scenarios
1. Create a video project
2. Update video project status
3. View video project details
4. Filter video projects list
5. View delivered video projects
6. Check status history tracking

---

## Implementation Notes

### DO NOT:
- Add fields like shoot_location, shoot_date, video_duration_minutes
- Use choice fields for categories
- Add complex features (cuts, voiceover)
- Modify existing projects app code
- Create ProductSubcategory model for video

### MUST DO:
- Use exact field types from projects app
- Mirror validation logic exactly
- Use UUID primary keys
- Keep field names consistent
- Use CharField for category fields
- Implement same service layer pattern

### Key Differences Summary:
1. Model prefix: "Video" instead of base name
2. HS_ID pattern: VP_00001 instead of A1, A2, etc.
3. No product_subcategory field in VideoProject
4. No task management models/views/forms
5. Different color scheme in templates (purple vs blue)

---

## Deployment Steps

### Development Environment
1. Create feature branch (already done: `feature/video-production-manager`)
2. Implement models following this plan exactly
3. Run migrations locally
4. Test all functionality
5. Commit changes to feature branch

### Production Deployment (PythonAnywhere)
```bash
# After merging to main
git pull origin main
python manage.py makemigrations video_production
python manage.py migrate video_production
python manage.py collectstatic
# Reload web app
```

### Post-Deployment
1. Create initial VideoProduct entries via admin
2. Create VideoProjectStatusOption entries via admin or data migration
3. Update navigation for VIDEO_PM users
4. Test create/read/update operations
5. Monitor for any issues

---

## Questions Resolved

### Q: Should category fields be choice fields?
**A: NO** - Projects app uses CharField for flexibility. Mirror exactly.

### Q: Should we add video-specific fields?
**A: NO** - Only include fields that exist in projects app (minus subcategory).

### Q: How should HS_ID generation work?
**A: VP_00001, VP_00002, etc.** - Different pattern from projects but same concept.

### Q: Do we need task management?
**A: NO** - Video production doesn't use task management features.

---

## Success Criteria

The implementation is successful when:
1. ✅ Video production app is a perfect mirror of projects app structure
2. ✅ No modifications to existing projects app code
3. ✅ VIDEO_PM users can create/view/update video projects
4. ✅ Status history tracks all changes
5. ✅ Forms validate exactly like projects app
6. ✅ Templates have same structure with purple theme
7. ✅ Service layer follows same patterns
8. ✅ No task management functionality included
9. ✅ No product subcategory field in video projects
10. ✅ Production deployment successful without breaking existing functionality
