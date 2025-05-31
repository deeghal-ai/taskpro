#locations/models.py
from django.db import models
import uuid

class Region(models.Model):
    """
    Represents a geographical region in our system.
    
    This model stores high-level geographical divisions that contain multiple cities.
    Each region has a unique name and tracks when it was created and last updated.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="The name of the region (e.g., 'North', 'South', 'East', 'West')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']  # This will order regions alphabetically by default
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'

    def __str__(self):
        """String representation of the Region"""
        return self.name

class City(models.Model):
    """
    Represents a city in our system.
    
    Each city belongs to a specific region and has a unique name within that region.
    The combination of city name and region creates a unique constraint to prevent duplicates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="The name of the city"
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,  # Prevents deletion of regions that have cities
        related_name='cities',
        help_text="The region this city belongs to"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['region', 'name']
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
        unique_together = ['name', 'region']  # Ensures city names are unique within a region

    def __str__(self):
        """String representation of the City"""
        return f"{self.name} ({self.region.name})"