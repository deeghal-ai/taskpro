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


def home_redirect(request):
    if request.user.is_authenticated:
        if request.user.role == 'DPM':
            return redirect('projects:project_list')
        elif request.user.role == 'TEAM_MEMBER':
            return redirect('projects:team_member_dashboard')
    return redirect('accounts:login')

urlpatterns = [
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
]