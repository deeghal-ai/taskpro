#accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash

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


