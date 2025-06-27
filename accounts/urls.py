#accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views
from .forms import CustomPasswordChangeForm, CustomPasswordResetForm

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    # Update the logout view with explicit configuration
    path('logout/', auth_views.LogoutView.as_view(
        # Explicitly set where to go after logout
        next_page=reverse_lazy('accounts:login'),
        # Don't show the intermediate template
        template_name=None
    ), name='logout'),
    
    # User Profile URLs
    path('profile/', views.profile_view, name='profile'),
    
    # Password Change URLs (for logged-in users)
    path('password/change/', views.password_change_view, name='password_change'),
    
    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # Password Reset URLs (for logged-out users who forgot password)
    path('password/reset/', views.CustomPasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.txt',
        html_email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        form_class=CustomPasswordResetForm,
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]