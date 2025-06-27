from django import forms
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with Bootstrap styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to form fields
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your current password'
        })
        
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your new password'
        })
        
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your new password'
        })
        
        # Update field labels
        self.fields['old_password'].label = 'Current Password'
        self.fields['new_password1'].label = 'New Password'
        self.fields['new_password2'].label = 'Confirm New Password'


class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form that accepts username or email"""
    
    email = forms.CharField(
        label="Username or Email",
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email address',
            'autocomplete': 'email'
        })
    )
    
    def clean_email(self):
        """Override to handle both username and email"""
        email_or_username = self.cleaned_data['email']
        
        # Try to find user by email first
        users = User.objects.filter(email__iexact=email_or_username)
        if not users.exists():
            # If no user found by email, try by username
            users = User.objects.filter(username__iexact=email_or_username)
            
        if not users.exists():
            # Don't reveal whether user exists or not (security best practice)
            # Just return the input - the get_users method will handle it
            pass
        
        return email_or_username
    
    def get_users(self, email):
        """Override to return users matching either email or username"""
        # First try by email
        users_by_email = User.objects.filter(
            email__iexact=email,
            is_active=True
        )
        
        # Then try by username if no email match
        users_by_username = User.objects.filter(
            username__iexact=email,
            is_active=True
        )
        
        # Combine querysets
        active_users = users_by_email.union(users_by_username)
        
        # Filter out users without email addresses (can't send reset email)
        return (u for u in active_users if u.has_usable_password() and u.email)


class UserProfileForm(forms.ModelForm):
    """Form for users to update their profile information, especially email"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            
        # Update field attributes
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'Enter your first name'
        })
        
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'Enter your last name'
        })
        
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter your email address',
            'type': 'email'
        })
        
        # Add help text for email field
        self.fields['email'].help_text = (
            "Adding an email address allows you to reset your password if you forget it."
        )
        
        # Make email required for better UX
        self.fields['email'].required = True
        
    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get('email')
        if email:
            # Check if another user already has this email
            existing_user = User.objects.filter(email=email).exclude(pk=self.instance.pk).first()
            if existing_user:
                raise ValidationError("This email address is already in use by another user.")
        return email 