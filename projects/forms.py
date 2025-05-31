# projects/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Project, ProductSubcategory, Product, ProjectStatusOption, ProductTask, ProjectTask, TaskAssignment, TaskAssignment, ActiveTimer, TimeSession, DailyTimeTotal
from locations.models import Region, City
from accounts.models import User
from datetime import timedelta, date
from .services import ProjectService

class DurationWidget(forms.TextInput):
    """Custom widget for duration input in HH:MM format"""
    template_name = 'django/forms/widgets/text.html'
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'placeholder': 'HH:MM'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        """Convert minutes to HH:MM format"""
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        hours = value // 60
        minutes = value % 60
        return f"{hours:02d}:{minutes:02d}"

    def value_from_datadict(self, data, files, name):
        """Convert submitted value to minutes"""
        value = data.get(name)
        if not value:
            return None
        try:
            hours, minutes = map(int, value.split(':'))
            return hours * 60 + minutes
        except (ValueError, TypeError):
            return None

class DurationFormField(forms.Field):
    """Custom form field for duration input"""
    widget = DurationWidget

    def __init__(self, *args, **kwargs):
        kwargs['widget'] = DurationWidget
        super().__init__(*args, **kwargs)

    def clean(self, value):
        """Validate and convert the duration value"""
        if not value:
            return None
        try:
            if isinstance(value, str):
                hours, minutes = map(int, value.split(':'))
                if hours < 0 or minutes < 0 or minutes >= 60:
                    raise ValidationError("Invalid time format. Use HH:MM")
                return hours * 60 + minutes
            return value
        except (ValueError, TypeError):
            raise ValidationError("Enter time in HH:MM format")


class ProjectCreateForm(forms.ModelForm):
    """
    A form for DPMs to create new projects. This form provides a user-friendly interface
    with appropriate validation and helpful error messages. It automatically handles
    certain fields like DPM assignment and expected TAT calculation.
    """
    
    # Add a field for status change comments that might be needed during creation
    status_change_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Optional comments about the initial status of this project"
    )

    class Meta:
        model = Project
        fields = [
            'opportunity_id',
            'project_type',
            'project_name',
            'builder_name',
            'city',
            'product',
            'product_subcategory',
            'package_id',
            'quantity',
            'purchase_date',
            'sales_confirmation_date',
            'account_manager',
            'current_status',
        ]
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'sales_confirmation_date': forms.DateInput(attrs={'type': 'date'}),
            'project_type': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Enter project type (optional)'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'product_subcategory': forms.Select(attrs={'class': 'form-select'}),
            'current_status': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'opportunity_id': 'Unique identifier for this project opportunity',
            'project_name': 'A descriptive name for the project',
            'builder_name': 'Name of the client/builder',
            'quantity': 'Number of units/items in this project',
            'package_id': 'Optional package identifier if applicable',
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the form with custom configurations. This includes:
        - Setting the logged-in user (DPM)
        - Configuring initial status options
        - Setting up field dependencies
        """
        # Get the user from kwargs before calling parent's __init__
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        # Add a clear empty label for the product_subcategory dropdown
        self.fields['product_subcategory'].empty_label = "-- Select Subcategory (Optional) --"
        
        # Filter status choices to show only active status options
        self.fields['current_status'].queryset = (
            self.fields['current_status'].queryset.filter(is_active=True)
            .order_by('order')
        )
        
        # Set initial status if available
        try:
            initial_status = self.fields['current_status'].queryset.first()
            self.fields['current_status'].initial = initial_status
        except:
            pass

    def clean(self):
        """
        Perform cross-field validation and business logic checks.
        This ensures data integrity and business rules are maintained.
        """
        cleaned_data = super().clean()
        
        # Ensure purchase_date is not after sales_confirmation_date
        purchase_date = cleaned_data.get('purchase_date')
        sales_date = cleaned_data.get('sales_confirmation_date')
        if purchase_date and sales_date and purchase_date > sales_date:
            raise ValidationError(
                {"purchase_date": "Purchase date cannot be after sales confirmation date"}
            )
        
        return cleaned_data

    def save(self, commit=True):
        """Save method that delegates to the service layer"""
        if not commit:
            return super().save(commit=False)
        
        # Form validation has already run, so we have cleaned_data
        cleaned_data = self.cleaned_data
        
        # Call service with form data
        success, result = ProjectService.create_project(
            project_data=cleaned_data,
            user=self.user
        )
        
        if not success:
            # Convert service errors to ValidationError
            raise ValidationError(result)
        
        return result
    

class ProjectStatusUpdateForm(forms.Form):
    """
    Form for updating a project's status with comments.
    
    We use a regular Form instead of ModelForm because we're not updating
    the entire project model, just the status and creating a history entry.
    """
    status = forms.ModelChoiceField(
        queryset=ProjectStatusOption.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=None,  # Don't allow empty selection
        help_text="Select the new status for this project"
    )
    
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter any comments about this status change'
        }),
        required=False,
        help_text="Optional: Add any relevant comments about this status change"
    )


class ProjectFilterForm(forms.Form):
    """
    Form for filtering the project list.
    All fields are optional to allow partial filtering.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )
    
    status = forms.ModelChoiceField(
        queryset=ProjectStatusOption.objects.filter(is_active=True),
        required=False,
        empty_label="All Statuses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        empty_label="All Products",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        empty_label="All Regions",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label="All Cities",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    dpm = forms.ModelChoiceField(
        queryset=User.objects.filter(role='DPM', is_active=True),
        required=False,
        empty_label="All DPMs",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the form with dynamic querysets.
        This allows us to update the city choices based on the selected region.
        """
        super().__init__(*args, **kwargs)
        
        # If a region is selected, filter cities accordingly
        if 'initial' in kwargs and kwargs['initial'].get('region'):
            region_id = kwargs['initial']['region']
            self.fields['city'].queryset = City.objects.filter(region_id=region_id)


class ProjectManagementForm(forms.ModelForm):
    """
    Form for DPMs to manage project setup and configuration.
    Combines project incharge assignment, completion date, and performance rating
    in a single form.
    """
    class Meta:
        model = Project
        fields = [
            'project_incharge',
            'expected_completion_date',
            'delivery_performance_rating'
        ]
        widgets = {
            'project_incharge': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select project incharge'
            }),
            'expected_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'delivery_performance_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '0.5',
                'placeholder': 'Rate from 1 to 5'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter project_incharge choices to show only team members
        team_members = User.objects.filter(
            role='TEAM_MEMBER',
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['project_incharge'].queryset = team_members
        
        # Add help texts
        self.fields['project_incharge'].help_text = (
            "Select the team member who will be in charge of this project"
        )
        self.fields['expected_completion_date'].help_text = (
            "When do you expect this project to be completed?"
        )
        self.fields['delivery_performance_rating'].help_text = (
            "Rate expected delivery performance (1-5)"
        )

    def clean(self):
        """
        Custom validation to ensure required fields are properly filled.
        """
        cleaned_data = super().clean()
        project_incharge = cleaned_data.get('project_incharge')
        expected_completion_date = cleaned_data.get('expected_completion_date')

        if not project_incharge:
            self.add_error('project_incharge', 'Project Incharge is required')
        
        if not expected_completion_date:
            self.add_error('expected_completion_date', 'Expected Completion Date is required')

        return cleaned_data


class ProjectTaskForm(forms.ModelForm):
    """
    Form for creating or updating project tasks.
    
    This form is used by DPMs to create tasks for a project. It handles:
    - Task selection from product-specific tasks
    - Task type specification
    - Time estimation
    """
    estimated_time = DurationFormField(
        label="Estimated Time",
        help_text="Enter estimated time in HH:MM format",
        required=True
    )

    class Meta:
        model = ProjectTask
        fields = [
            'product_task',
            'task_type',
            'estimated_time'
        ]
        widgets = {
            'product_task': forms.Select(attrs={
                'class': 'form-select'
            }),
            'task_type': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, project=None, *args, **kwargs):
        """
        Initialize the form with project-specific choices.
        """
        self.project = project
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.project:
            # Filter product tasks for this project's product
            self.fields['product_task'].queryset = ProductTask.objects.filter(
                product=self.project.product,
                is_active=True
            ).order_by('name')
            
            # Add helpful text
            self.fields['estimated_time'].help_text = 'Estimated time in hours'

    def clean_estimated_time(self):
        """Validate that estimated time is positive."""
        time = self.cleaned_data.get('estimated_time')
        if time and time < 1:
            raise ValidationError("Estimated time must be at least 1 minute")
        return time
    
    def save(self, commit=True):
        """Save method that delegates to the service layer"""
        if not commit:
            return super().save(commit=False)
            
        # Ensure we have the necessary context
        if not self.project or not self.user:
            raise ValidationError("Project and User must be provided to save this form")
            
        # Form validation has already run, so we have cleaned_data
        cleaned_data = self.cleaned_data
        
        # Call service with form data
        from .services import ProjectService
        success, result = ProjectService.create_project_task(
            project_id=self.project.id,
            task_data=cleaned_data,
            dpm=self.user
        )
        
        if not success:
            # Convert service errors to ValidationError
            raise ValidationError(result)
        
        return result


class TaskAssignmentForm(forms.ModelForm):
    """
    Form for creating new task assignments.
    This form handles the initial assignment of a task to a team member.
    """
    projected_hours = DurationFormField(
        label="Projected Hours",
        help_text="Enter projected time in HH:MM format",
        required=True
    )

    class Meta:
        model = TaskAssignment
        fields = [
            'assigned_to',
            'projected_hours',
            'sub_task',
            'rework_type',
            'expected_delivery_date'
        ]
        widgets = {
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sub_task': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'rework_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'expected_delivery_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop('task', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        team_members = User.objects.filter(
            role='TEAM_MEMBER',
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['assigned_to'].queryset = team_members
    
    def save(self, commit=True):
        """Save method that delegates to the service layer"""
        if not commit:
            return super().save(commit=False)
            
        # Ensure we have the necessary context
        if not self.task or not self.user:
            raise ValidationError("Task and User must be provided to save this form")
            
        # Form validation has already run, so we have cleaned_data
        cleaned_data = self.cleaned_data
        
        # Call service with form data
        from .services import ProjectService
        success, result = ProjectService.create_task_assignment(
            task_id=self.task.id,
            assignment_data=cleaned_data,
            dpm=self.user
        )
        
        if not success:
            # Convert service errors to ValidationError
            raise ValidationError(result)
        
        return result


class TaskAssignmentUpdateForm(forms.ModelForm):
    """
    Form for updating task assignments.
    UPDATED: Allows quality rating updates for completed assignments.
    """
    projected_hours = DurationFormField(
        label="Projected Hours",
        help_text="Enter projected time in HH:MM format",
        required=False
    )

    class Meta:
        model = TaskAssignment
        fields = [
            'projected_hours',
            'expected_delivery_date',
            'quality_rating',  # KEPT: Allow quality rating updates
            'is_active'
        ]
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'quality_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '0.5'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Check if this is for a completed assignment
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # If assignment is completed, only allow quality rating updates
        if instance and instance.is_completed:
            # Make other fields read-only for completed assignments
            self.fields['projected_hours'].widget.attrs['readonly'] = True
            self.fields['expected_delivery_date'].widget.attrs['readonly'] = True
            self.fields['is_active'].widget.attrs['disabled'] = True
            
            # Add help text for completed assignments
            self.fields['quality_rating'].help_text = (
                "Rate the quality of work for this completed assignment (1-5)"
            )
            
            # Make quality rating required for completed assignments
            self.fields['quality_rating'].required = True
        else:
            # For active assignments, make all fields optional for partial updates
            for field in self.fields:
                self.fields[field].required = False

    def clean(self):
        """
        Custom validation to ensure partial updates work correctly
        """
        cleaned_data = super().clean()
        
        # If this is an existing instance, merge unchanged fields
        if self.instance and self.instance.pk:
            for field in self.fields:
                if cleaned_data.get(field) is None and not self.instance.is_completed:
                    cleaned_data[field] = getattr(self.instance, field)
        print("Form received data:", self.data)  # Debug what the form receives
        print("Cleaned data:", cleaned_data) 
        
        return cleaned_data
    

class TimerStopForm(forms.Form):
    """
    Form for stopping a timer with optional description.
    """
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: Describe what you worked on during this session'
        }),
        required=False,
        help_text="Optional description of work completed in this session"
    )
    
    is_completed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check this box if you want to mark the entire assignment as completed"
    )


class ManualTimeEntryForm(forms.Form):
    """
    Form for adding manual time entries.
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': date.today().isoformat()  # Can't add future dates
        }),
        initial=date.today,
        help_text="The date when you performed this work"
    )
    
    duration_hours = forms.IntegerField(
        min_value=0,
        max_value=23,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '23'
        }),
        help_text="Hours worked"
    )
    
    duration_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '59'
        }),
        help_text="Minutes worked"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: Describe what you worked on'
        }),
        required=False,
        help_text="Optional description of work completed"
    )
    
    is_completed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check this box if you want to mark the entire assignment as completed"
    )
    
    def clean(self):
        """
        Validate that at least some time is entered.
        """
        cleaned_data = super().clean()
        hours = cleaned_data.get('duration_hours', 0)
        minutes = cleaned_data.get('duration_minutes', 0)
        
        if hours == 0 and minutes == 0:
            raise ValidationError("Please enter at least 1 minute of work time.")
        
        # Check that date is not in the future
        work_date = cleaned_data.get('date')
        if work_date and work_date > date.today():
            raise ValidationError("Work date cannot be in the future.")
        
        return cleaned_data


class EditSessionDurationForm(forms.Form):
    """
    Form for editing individual timer session durations.
    Only allows editing duration, not start/end times.
    """
    session_id = forms.UUIDField(widget=forms.HiddenInput())
    
    duration_hours = forms.IntegerField(
        min_value=0,
        max_value=23,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '23'
        }),
        help_text="Hours for this session"
    )
    
    duration_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '59'
        }),
        help_text="Minutes for this session"
    )
    
    def __init__(self, *args, **kwargs):
        # Get initial values from existing session if provided
        session = kwargs.pop('session', None)
        
        super().__init__(*args, **kwargs)
        
        if session:
            # Set hidden field
            self.fields['session_id'].initial = session.id
            
            # Pre-populate with current duration
            if session.duration_minutes:
                hours = session.duration_minutes // 60
                minutes = session.duration_minutes % 60
                self.fields['duration_hours'].initial = hours
                self.fields['duration_minutes'].initial = minutes
            else:
                self.fields['duration_hours'].initial = 0
                self.fields['duration_minutes'].initial = 0
    
    def clean(self):
        """
        Validate that at least some time is entered.
        """
        cleaned_data = super().clean()
        hours = cleaned_data.get('duration_hours', 0)
        minutes = cleaned_data.get('duration_minutes', 0)
        
        if hours == 0 and minutes == 0:
            raise ValidationError("Duration must be at least 1 minute.")
        
        # Calculate total minutes for validation
        total_minutes = (hours * 60) + minutes
        if total_minutes > 1440:  # 24 hours
            raise ValidationError("Duration cannot exceed 24 hours.")
        
        return cleaned_data
    
    def get_total_minutes(self):
        """
        Helper method to get total minutes from form data.
        """
        if self.is_valid():
            hours = self.cleaned_data.get('duration_hours', 0)
            minutes = self.cleaned_data.get('duration_minutes', 0)
            return (hours * 60) + minutes
        return 0


class DailyRosterFilterForm(forms.Form):
    """
    Form for filtering daily roster view (team member's daily time breakdown).
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        initial=date.today,
        help_text="Select date to view time breakdown"
    )
    
    week_view = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Show entire week instead of single day"
    )

class AddMiscHoursForm(forms.Form):
    """
    Form for adding miscellaneous hours to daily roster.
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'max': date.today().isoformat()  # Can't add future dates
        }),
        initial=date.today,
        help_text="Date when the miscellaneous work was performed"
    )
    
    activity = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Team meeting, Training, Admin work'
        }),
        help_text="Brief description of the activity"
    )
    
    duration_hours = forms.IntegerField(
        min_value=0,
        max_value=23,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '23'
        }),
        help_text="Hours spent"
    )
    
    duration_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '59'
        }),
        help_text="Minutes spent"
    )
    
    def clean(self):
        """
        Validate that at least some time is entered and date is valid.
        """
        cleaned_data = super().clean()
        hours = cleaned_data.get('duration_hours', 0)
        minutes = cleaned_data.get('duration_minutes', 0)
        work_date = cleaned_data.get('date')
        
        if hours == 0 and minutes == 0:
            raise ValidationError("Duration must be at least 1 minute.")
        
        # Check that date is not in the future
        if work_date and work_date > date.today():
            raise ValidationError("Work date cannot be in the future.")
        
        return cleaned_data
    
    def get_total_minutes(self):
        """
        Helper method to get total minutes from form data.
        """
        if self.is_valid():
            hours = self.cleaned_data.get('duration_hours', 0)
            minutes = self.cleaned_data.get('duration_minutes', 0)
            return (hours * 60) + minutes
        return 0