"""
Video Production Forms - mirrors projects/forms.py
Simplified forms without video-specific complexity.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import VideoProject, VideoProjectStatusOption, VideoProduct
from locations.models import City, Region
from accounts.models import User

class VideoProjectCreateForm(forms.ModelForm):
    """
    Form for creating video projects - mirrors Project creation form from projects app.
    """
    
    class Meta:
        model = VideoProject
        fields = [
            'opportunity_id', 'project_type', 'project_name', 'builder_name', 
            'city', 'product', 'package_id', 'quantity',
            'purchase_date', 'sales_confirmation_date', 
            'expected_completion_date', 'account_manager'
        ]
        widgets = {
            'opportunity_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter opportunity ID'}),
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter project name'}),
            'builder_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter builder/client name'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'package_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter package ID'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sales_confirmation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'account_manager': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter account manager name'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for foreign key fields
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['product'].queryset = VideoProduct.objects.filter(is_active=True).order_by('name')
        
        # Set required fields
        self.fields['project_name'].required = True
        self.fields['builder_name'].required = True
        self.fields['city'].required = True
        self.fields['product'].required = True
        
    def clean_opportunity_id(self):
        """Validate opportunity ID uniqueness"""
        opportunity_id = self.cleaned_data.get('opportunity_id')
        if opportunity_id:
            # Check if opportunity_id already exists
            existing = VideoProject.objects.filter(opportunity_id=opportunity_id)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("A video project with this opportunity ID already exists.")
        return opportunity_id
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        purchase_date = cleaned_data.get('purchase_date')
        expected_completion_date = cleaned_data.get('expected_completion_date')
        
        if purchase_date and expected_completion_date:
            if expected_completion_date <= purchase_date:
                raise ValidationError("Expected completion date must be after purchase date.")
        
        return cleaned_data

class VideoProjectEditForm(forms.ModelForm):
    """
    Form for editing video projects - mirrors Project edit form from projects app.
    """
    
    class Meta:
        model = VideoProject
        fields = [
            'project_name', 'builder_name', 'city', 'product',
            'package_id', 'quantity', 'expected_tat', 'expected_completion_date',
            'account_manager'
        ]
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control'}),
            'builder_name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'package_id': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'expected_tat': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'account_manager': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for foreign key fields
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['product'].queryset = VideoProduct.objects.filter(is_active=True).order_by('name')

class VideoProjectStatusUpdateForm(forms.Form):
    """
    Form for updating video project status - mirrors projects status update form.
    """
    status = forms.ModelChoiceField(
        queryset=VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label="New Status"
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Enter status update comments (optional)'
        }),
        required=False,
        label="Comments"
    )

class VideoProjectFilterForm(forms.Form):
    """
    Form for filtering video project lists - mirrors projects filter form.
    """
    
    status = forms.ModelChoiceField(
        queryset=VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
        required=False,
        empty_label="All Statuses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    region = forms.ModelChoiceField(
        queryset=Region.objects.all().order_by('name'),
        required=False,
        empty_label="All Regions",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=False,
        empty_label="All Cities",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    product = forms.ModelChoiceField(
        queryset=VideoProduct.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label="All Video Products",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    video_pm = forms.ModelChoiceField(
        queryset=User.objects.filter(role='VIDEO_PM', is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label="All Video PMs",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Search projects...'
        }),
        help_text="Search by project name, builder name, HS ID, or opportunity ID"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date From"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date To"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure fresh querysets
        self.fields['status'].queryset = VideoProjectStatusOption.objects.filter(is_active=True).order_by('order')
        self.fields['region'].queryset = Region.objects.all().order_by('name')
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['product'].queryset = VideoProduct.objects.filter(is_active=True).order_by('name')
        self.fields['video_pm'].queryset = User.objects.filter(role='VIDEO_PM', is_active=True).order_by('first_name', 'last_name')