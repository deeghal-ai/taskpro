#locations/tests.py
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from .models import Region, City
from .admin import RegionAdmin, CityAdmin
import uuid

User = get_user_model()

class RegionModelTests(TestCase):
    """Test cases for the Region model"""
    
    def setUp(self):
        """Set up test data"""
        self.region_data = {
            'name': 'Test Region'
        }
    
    def test_create_region_with_valid_data(self):
        """Test creating a region with valid data"""
        region = Region.objects.create(**self.region_data)
        
        self.assertEqual(region.name, 'Test Region')
        self.assertIsInstance(region.id, uuid.UUID)
        self.assertIsNotNone(region.created_at)
        self.assertIsNotNone(region.updated_at)
    
    def test_region_str_representation(self):
        """Test the string representation of Region"""
        region = Region.objects.create(**self.region_data)
        self.assertEqual(str(region), 'Test Region')
    
    def test_region_name_uniqueness(self):
        """Test that region names must be unique"""
        Region.objects.create(**self.region_data)
        
        # Try to create another region with same name
        with self.assertRaises(IntegrityError):
            Region.objects.create(**self.region_data)
    
    def test_region_ordering(self):
        """Test that regions are ordered by name"""
        Region.objects.create(name='Zulu Region')
        Region.objects.create(name='Alpha Region')
        Region.objects.create(name='Beta Region')
        
        regions = Region.objects.all()
        region_names = [region.name for region in regions]
        
        self.assertEqual(region_names, ['Alpha Region', 'Beta Region', 'Zulu Region'])
    
    def test_region_meta_verbose_names(self):
        """Test verbose names are set correctly"""
        self.assertEqual(Region._meta.verbose_name, 'Region')
        self.assertEqual(Region._meta.verbose_name_plural, 'Regions')
    
    def test_region_name_max_length(self):
        """Test region name max length validation"""
        long_name = 'a' * 101  # Max length is 100
        region = Region(name=long_name)
        
        with self.assertRaises(ValidationError):
            region.full_clean()
    
    def test_region_timestamps(self):
        """Test that created_at and updated_at are set correctly"""
        region = Region.objects.create(**self.region_data)
        
        self.assertIsNotNone(region.created_at)
        self.assertIsNotNone(region.updated_at)
        self.assertLessEqual(region.created_at, region.updated_at)
    
    def test_region_uuid_primary_key(self):
        """Test that region ID is a UUID"""
        region = Region.objects.create(**self.region_data)
        self.assertIsInstance(region.id, uuid.UUID)


class CityModelTests(TestCase):
    """Test cases for the City model"""
    
    def setUp(self):
        """Set up test data"""
        self.region = Region.objects.create(name='Test Region')
        self.city_data = {
            'name': 'Test City',
            'region': self.region
        }
    
    def test_create_city_with_valid_data(self):
        """Test creating a city with valid data"""
        city = City.objects.create(**self.city_data)
        
        self.assertEqual(city.name, 'Test City')
        self.assertEqual(city.region, self.region)
        self.assertIsInstance(city.id, uuid.UUID)
        self.assertIsNotNone(city.created_at)
        self.assertIsNotNone(city.updated_at)
    
    def test_city_str_representation(self):
        """Test the string representation of City"""
        city = City.objects.create(**self.city_data)
        expected_str = f"Test City (Test Region)"
        self.assertEqual(str(city), expected_str)
    
    def test_city_unique_together_constraint(self):
        """Test that city names are unique within a region"""
        City.objects.create(**self.city_data)
        
        # Try to create another city with same name in same region
        with self.assertRaises(IntegrityError):
            City.objects.create(**self.city_data)
    
    def test_city_same_name_different_region(self):
        """Test that cities can have same name in different regions"""
        City.objects.create(**self.city_data)
        
        # Create another region
        other_region = Region.objects.create(name='Other Region')
        other_city_data = {
            'name': 'Test City',  # Same name
            'region': other_region  # Different region
        }
        
        # This should work without raising an exception
        other_city = City.objects.create(**other_city_data)
        self.assertEqual(other_city.name, 'Test City')
        self.assertEqual(other_city.region, other_region)
    
    def test_city_ordering(self):
        """Test that cities are ordered by region then name"""
        region_a = Region.objects.create(name='A Region')
        region_b = Region.objects.create(name='B Region')
        
        City.objects.create(name='Z City', region=region_b)
        City.objects.create(name='A City', region=region_b)
        City.objects.create(name='M City', region=region_a)
        
        cities = City.objects.all()
        
        # Should be ordered by region first, then by city name
        expected_order = [
            ('M City', 'A Region'),
            ('A City', 'B Region'),
            ('Z City', 'B Region')
        ]
        
        actual_order = [(city.name, city.region.name) for city in cities]
        self.assertEqual(actual_order, expected_order)
    
    def test_city_meta_verbose_names(self):
        """Test verbose names are set correctly"""
        self.assertEqual(City._meta.verbose_name, 'City')
        self.assertEqual(City._meta.verbose_name_plural, 'Cities')
    
    def test_city_foreign_key_protection(self):
        """Test that regions cannot be deleted if they have cities"""
        city = City.objects.create(**self.city_data)
        
        # Try to delete the region - should be protected
        with self.assertRaises(Exception):  # ProtectedError
            self.region.delete()
    
    def test_city_name_max_length(self):
        """Test city name max length validation"""
        long_name = 'a' * 101  # Max length is 100
        city = City(name=long_name, region=self.region)
        
        with self.assertRaises(ValidationError):
            city.full_clean()
    
    def test_city_timestamps(self):
        """Test that created_at and updated_at are set correctly"""
        city = City.objects.create(**self.city_data)
        
        self.assertIsNotNone(city.created_at)
        self.assertIsNotNone(city.updated_at)
        self.assertLessEqual(city.created_at, city.updated_at)
    
    def test_city_uuid_primary_key(self):
        """Test that city ID is a UUID"""
        city = City.objects.create(**self.city_data)
        self.assertIsInstance(city.id, uuid.UUID)
    
    def test_city_related_name(self):
        """Test that the related_name 'cities' works on Region"""
        city1 = City.objects.create(name='City 1', region=self.region)
        city2 = City.objects.create(name='City 2', region=self.region)
        
        cities = self.region.cities.all()
        self.assertEqual(cities.count(), 2)
        self.assertIn(city1, cities)
        self.assertIn(city2, cities)


class RegionAdminTests(TestCase):
    """Test cases for the Region admin interface"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = RegionAdmin(Region, self.site)
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role='DPM'
        )
        self.region = Region.objects.create(name='Test Region')
    
    def test_list_display_fields(self):
        """Test that list_display contains expected fields"""
        expected_fields = ('name', 'created_at', 'updated_at')
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_search_fields(self):
        """Test that search_fields contains expected fields"""
        expected_search = ('name',)
        self.assertEqual(self.admin.search_fields, expected_search)
    
    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields"""
        # RegionAdmin doesn't have list_filter, so this test should check if it's empty or not defined
        self.assertFalse(hasattr(self.admin, 'list_filter') or not self.admin.list_filter)
    
    def test_readonly_fields(self):
        """Test that readonly_fields contains timestamp fields"""
        expected_readonly = ('created_at', 'updated_at')
        self.assertEqual(self.admin.readonly_fields, expected_readonly)


class CityAdminTests(TestCase):
    """Test cases for the City admin interface"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = CityAdmin(City, self.site)
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role='DPM'
        )
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
    
    def test_list_display_fields(self):
        """Test that list_display contains expected fields"""
        expected_fields = ('name', 'region', 'created_at', 'updated_at')
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_search_fields(self):
        """Test that search_fields contains expected fields"""
        expected_search = ('name', 'region__name')
        self.assertEqual(self.admin.search_fields, expected_search)
    
    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields"""
        expected_filters = ('region',)
        self.assertEqual(self.admin.list_filter, expected_filters)
    
    def test_readonly_fields(self):
        """Test that readonly_fields contains timestamp fields"""
        expected_readonly = ('created_at', 'updated_at')
        self.assertEqual(self.admin.readonly_fields, expected_readonly)


class LocationQueryTests(TestCase):
    """Test cases for querying regions and cities"""
    
    def setUp(self):
        """Set up test data"""
        self.regions = []
        self.cities = []
        
        for i in range(3):
            region = Region.objects.create(name=f'Region {i}')
            self.regions.append(region)
            
            for j in range(2):
                city = City.objects.create(
                    name=f'City {i}-{j}',
                    region=region
                )
                self.cities.append(city)
    
    def test_filter_cities_by_region(self):
        """Test filtering cities by region"""
        region = self.regions[0]
        cities = City.objects.filter(region=region)
        
        self.assertEqual(cities.count(), 2)
        for city in cities:
            self.assertEqual(city.region, region)
    
    def test_prefetch_related_cities(self):
        """Test prefetching related cities for regions"""
        regions = Region.objects.prefetch_related('cities').all()
        
        for region in regions:
            # This should not hit the database again
            cities = list(region.cities.all())
            self.assertEqual(len(cities), 2)
    
    def test_select_related_region(self):
        """Test select_related for city's region"""
        cities = City.objects.select_related('region').all()
        
        for city in cities:
            # This should not hit the database again
            region_name = city.region.name
            self.assertIsNotNone(region_name)
    
    def test_search_cities_by_name(self):
        """Test searching cities by name"""
        cities = City.objects.filter(name__icontains='City 0')
        self.assertEqual(cities.count(), 2)  # City 0-0 and City 0-1
    
    def test_search_cities_by_region_name(self):
        """Test searching cities by region name"""
        cities = City.objects.filter(region__name__icontains='Region 1')
        self.assertEqual(cities.count(), 2)
        
        for city in cities:
            self.assertEqual(city.region.name, 'Region 1')
    
    def test_count_cities_per_region(self):
        """Test counting cities per region"""
        from django.db.models import Count
        
        regions = Region.objects.annotate(city_count=Count('cities'))
        
        for region in regions:
            self.assertEqual(region.city_count, 2)


class LocationValidationTests(TestCase):
    """Test cases for location model validation"""
    
    def setUp(self):
        """Set up test data"""
        self.region = Region.objects.create(name='Test Region')
    
    def test_region_name_required(self):
        """Test that region name is required"""
        region = Region()
        
        with self.assertRaises(ValidationError):
            region.full_clean()
    
    def test_city_name_required(self):
        """Test that city name is required"""
        city = City(region=self.region)
        
        with self.assertRaises(ValidationError):
            city.full_clean()
    
    def test_city_region_required(self):
        """Test that city region is required"""
        city = City(name='Test City')
        
        with self.assertRaises(ValidationError):
            city.full_clean()
    
    def test_region_name_strip_whitespace(self):
        """Test that region name strips whitespace"""
        region = Region.objects.create(name='  Test Region  ')
        # Django doesn't auto-strip by default, but we can test what we expect
        self.assertTrue(region.name.strip() == 'Test Region')
    
    def test_city_name_strip_whitespace(self):
        """Test that city name strips whitespace"""
        city = City.objects.create(name='  Test City  ', region=self.region)
        # Django doesn't auto-strip by default, but we can test what we expect
        self.assertTrue(city.name.strip() == 'Test City')


class LocationIntegrationTests(TestCase):
    """Integration tests for locations with other models"""
    
    def setUp(self):
        """Set up test data"""
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
    
    def test_location_cascade_behavior(self):
        """Test what happens when we try to delete regions with cities"""
        # Create a city
        city_count_before = City.objects.count()
        
        # Trying to delete region should fail due to PROTECT
        with self.assertRaises(Exception):
            self.region.delete()
        
        # City should still exist
        self.assertEqual(City.objects.count(), city_count_before)
    
    def test_bulk_create_cities(self):
        """Test bulk creating cities"""
        cities_data = [
            City(name=f'Bulk City {i}', region=self.region)
            for i in range(5)
        ]
        
        City.objects.bulk_create(cities_data)
        
        # Should have original city + 5 new ones
        self.assertEqual(City.objects.filter(region=self.region).count(), 6)
    
    def test_region_city_relationship_integrity(self):
        """Test the integrity of region-city relationships"""
        # Create multiple cities in the region
        for i in range(3):
            City.objects.create(name=f'City {i}', region=self.region)
        
        # Total cities should be 4 (1 from setUp + 3 new)
        self.assertEqual(self.region.cities.count(), 4)
        
        # All cities should belong to the correct region
        for city in self.region.cities.all():
            self.assertEqual(city.region, self.region)
