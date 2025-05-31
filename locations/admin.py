#locations/admin.py
from django.contrib import admin
from .models import Region, City

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the Region model.
    """
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the City model.
    """
    list_display = ('name', 'region', 'created_at', 'updated_at')
    list_filter = ('region',)
    search_fields = ('name', 'region__name')
    ordering = ('region', 'name')
    readonly_fields = ('created_at', 'updated_at')