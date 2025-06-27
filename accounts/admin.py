#accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import User

class CustomUserAdmin(UserAdmin):
    """Custom admin for User model with password reset capabilities"""
    
    list_display = ('username', 'email', 'role', 'is_active', 'has_email_for_reset')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # Add custom field to show if user can reset password
    def has_email_for_reset(self, obj):
        return bool(obj.email)
    has_email_for_reset.boolean = True
    has_email_for_reset.short_description = 'Can Reset Password'
    
    # Add fieldsets for better organization
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('TaskPro Settings', {'fields': ('role',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    actions = ['reset_password_for_selected_users']
    
    def reset_password_for_selected_users(self, request, queryset):
        """Custom admin action to reset passwords for users without email"""
        count = 0
        for user in queryset:
            # Generate a temporary password
            temp_password = f"temp{user.username}123"
            user.set_password(temp_password)
            user.save()
            count += 1
            
        self.message_user(
            request,
            f"Reset passwords for {count} users. Temporary password format: temp[username]123",
            messages.SUCCESS
        )
    
    reset_password_for_selected_users.short_description = "Reset password (for users without email)"

admin.site.register(User, CustomUserAdmin)