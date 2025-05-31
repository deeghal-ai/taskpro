#accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for creating new users. This extends Django's built-in
    UserCreationForm to include our custom fields like 'role'.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    """
    Custom form for modifying existing users. This extends Django's built-in
    UserChangeForm to include our custom fields.
    """
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'first_name', 'last_name')

class CustomUserAdmin(BaseUserAdmin):
    """
    Custom admin interface configuration for our User model. This builds upon
    Django's built-in UserAdmin while adding support for our custom fields.
    """
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    # Fields to display in the user list
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    
    # Fields available for filtering in the right sidebar
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Organization of fields in the user detail form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fields shown when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )
    
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

# Register the new admin class with our custom User model
admin.site.register(User, CustomUserAdmin)