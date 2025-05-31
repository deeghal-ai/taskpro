#accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

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
]