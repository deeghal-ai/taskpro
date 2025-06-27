#pms/urls.py
"""
URL configuration for pms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.views import LoginView
from django.contrib import admin
from django.http import HttpResponse


def home_redirect(request):
    """Proper home redirect without loops"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            if request.user.role == 'DPM':
                return redirect('/projects/')  # Use direct URL instead of name
            elif request.user.role == 'TEAM_MEMBER':
                return redirect('/projects/tasks/my-assignments/')  # Direct URL
        return redirect('/projects/')  # Default for authenticated users
    return redirect('/accounts/login/')  # Direct URL for unauthenticated

urlpatterns = [
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
]