#accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import CustomPasswordChangeForm, UserProfileForm
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@login_required
def profile_view(request):
    """View for users to see and edit their profile, especially email address"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            
            # If user added an email, let them know about password reset
            if user.email and not request.session.get('email_added_message_shown'):
                messages.info(request, 'Great! Now you can use password reset if you ever forget your password.')
                request.session['email_added_message_shown'] = True
                
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

@login_required  
def password_change_view(request):
    """Custom password change view with better UX"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})

class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that sends proper HTML emails"""
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email` with proper HTML formatting.
        """
        subject = render_to_string(subject_template_name, context)
        # Email subject must not contain newlines
        subject = ''.join(subject.splitlines())
        
        # Render the HTML template
        html_content = render_to_string(html_email_template_name, context)
        
        # Create a plain text version from HTML (fallback)
        text_content = strip_tags(html_content)
        
        # Create the email
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,  # Plain text version
            from_email=from_email,
            to=[to_email]
        )
        
        # Attach the HTML version
        email_message.attach_alternative(html_content, "text/html")
        
        # Send the email with logging
        try:
            result = email_message.send()
            logger.info(f"Password reset email sent to {to_email}. Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            raise
