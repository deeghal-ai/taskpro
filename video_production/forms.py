from django import forms
from django.core.exceptions import ValidationError
from .models import VideoProject, VideoProjectStatusOption, VideoCut, VoiceoverScript, VideoProduct
from locations.models import City

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
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter project name'}),
            'builder_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter builder/client name'}),
            'opportunity_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter opportunity ID'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'video_product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'production_vendor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter video production agency name'}),
            'shoot_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter shoot location (optional)'}),
            'shoot_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'video_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Duration in minutes'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'voiceover_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_cuts_allowed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10, 'value': 7}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for foreign key fields
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['video_product'].queryset = VideoProduct.objects.filter(is_active=True).order_by('name')
        
        # Set required fields
        self.fields['opportunity_id'].required = True
        self.fields['project_name'].required = True
        self.fields['builder_name'].required = True
        self.fields['city'].required = True
        self.fields['video_product'].required = True
        self.fields['production_vendor'].required = True
        self.fields['purchase_date'].required = True
        self.fields['expected_completion_date'].required = True
        
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

class VideoProjectStatusUpdateForm(forms.Form):
    """Form for updating video project status"""
    status = forms.ModelChoiceField(
        queryset=VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter status update comments (optional)'}),
        required=False
    )

class VideoCutSubmissionForm(forms.Form):
    """Form for submitting video cuts"""
    cut_number = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        help_text="Enter the cut number (1-10)"
    )
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        if self.project:
            self.fields['cut_number'].max_value = self.project.max_cuts_allowed
            current_cut = self.project.current_cut_number
            suggested_cut = current_cut + 1 if current_cut < self.project.max_cuts_allowed else current_cut
            self.fields['cut_number'].initial = suggested_cut
    
    def clean_cut_number(self):
        """Validate cut number"""
        cut_number = self.cleaned_data.get('cut_number')
        if self.project and cut_number:
            if cut_number > self.project.max_cuts_allowed:
                raise ValidationError(f"Cut number cannot exceed {self.project.max_cuts_allowed} (max cuts allowed for this project).")
        return cut_number

class VideoCutFeedbackForm(forms.Form):
    """Form for providing feedback on video cuts"""
    cut_number = forms.IntegerField(
        widget=forms.HiddenInput()
    )
    client_feedback = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter client feedback for this cut'}),
        required=True,
        help_text="Provide detailed feedback for the video cut"
    )
    request_rework = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check if rework is required"
    )

class VoiceoverScriptForm(forms.ModelForm):
    """Form for submitting voiceover scripts"""
    
    class Meta:
        model = VoiceoverScript
        fields = ['script_content']
        widgets = {
            'script_content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6, 
                'placeholder': 'Enter the voiceover script content...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['script_content'].required = True
        self.fields['script_content'].help_text = "Enter the complete voiceover script for this video project"

class VideoProjectFilterForm(forms.Form):
    """Form for filtering video project lists"""
    
    status = forms.ModelChoiceField(
        queryset=VideoProjectStatusOption.objects.filter(is_active=True).order_by('order'),
        required=False,
        empty_label="All Statuses",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    city = forms.ModelChoiceField(
        queryset=City.objects.all().order_by('name'),
        required=False,
        empty_label="All Cities",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    video_product = forms.ModelChoiceField(
        queryset=VideoProduct.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label="All Video Products",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vendor = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter vendor name'}),
        help_text="Search by production vendor name"
    )
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search projects...'}),
        help_text="Search by project name, builder name, HS ID, or opportunity ID"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set fresh querysets
        self.fields['status'].queryset = VideoProjectStatusOption.objects.filter(is_active=True).order_by('order')
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['video_product'].queryset = VideoProduct.objects.filter(is_active=True).order_by('name')

class VideoProjectEditForm(forms.ModelForm):
    """Form for editing existing video projects"""
    
    class Meta:
        model = VideoProject
        fields = [
            'project_name', 'builder_name', 'production_vendor',
            'shoot_location', 'shoot_date', 'video_duration_minutes',
            'expected_completion_date', 'voiceover_required', 'max_cuts_allowed'
        ]
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control'}),
            'builder_name': forms.TextInput(attrs={'class': 'form-control'}),
            'production_vendor': forms.TextInput(attrs={'class': 'form-control'}),
            'shoot_location': forms.TextInput(attrs={'class': 'form-control'}),
            'shoot_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'video_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'voiceover_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_cuts_allowed': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
        }
    
    def clean_max_cuts_allowed(self):
        """Validate max cuts allowed"""
        max_cuts = self.cleaned_data.get('max_cuts_allowed')
        if max_cuts and max_cuts < 1:
            raise ValidationError("Maximum cuts allowed must be at least 1.")
        if max_cuts and max_cuts > 10:
            raise ValidationError("Maximum cuts allowed cannot exceed 10.")
        return max_cuts 