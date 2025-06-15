#accounts/tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from .models import User
from .admin import CustomUserAdmin
import uuid

User = get_user_model()

class UserModelTests(TestCase):
    """Test cases for the custom User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'TEAM_MEMBER'
        }
    
    def test_create_user_with_valid_data(self):
        """Test creating a user with valid data"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'TEAM_MEMBER')
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_dpm_user(self):
        """Test creating a DPM user automatically gets staff privileges"""
        user_data = self.user_data.copy()
        user_data['role'] = 'DPM'
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.role, 'DPM')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_create_team_member_user(self):
        """Test creating a team member user doesn't get staff privileges"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.role, 'TEAM_MEMBER')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_str_representation(self):
        """Test the string representation of User"""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.username} - Team Member"
        self.assertEqual(str(user), expected_str)
    
    def test_user_role_choices(self):
        """Test that only valid role choices are allowed"""
        # Valid role
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.role, 'TEAM_MEMBER')
        
        # Test DPM role
        user_data = self.user_data.copy()
        user_data['username'] = 'dpmuser'
        user_data['role'] = 'DPM'
        dpm_user = User.objects.create_user(**user_data)
        self.assertEqual(dpm_user.role, 'DPM')
    
    def test_user_uuid_primary_key(self):
        """Test that user ID is a UUID"""
        user = User.objects.create_user(**self.user_data)
        self.assertIsInstance(user.id, uuid.UUID)
    
    def test_user_timestamps(self):
        """Test that created_at and updated_at are set correctly"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertLessEqual(user.created_at, user.updated_at)
    
    def test_user_save_method_dpm_promotion(self):
        """Test that save method promotes DPM users to staff/superuser"""
        # Create as team member first
        user = User.objects.create_user(**self.user_data)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
        # Change to DPM
        user.role = 'DPM'
        user.save()
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_get_role_display(self):
        """Test the get_role_display method returns human readable role"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_role_display(), 'Team Member')
        
        user.role = 'DPM'
        self.assertEqual(user.get_role_display(), 'Project Manager')
    
    def test_username_uniqueness(self):
        """Test that usernames must be unique"""
        User.objects.create_user(**self.user_data)
        
        # Try to create another user with same username
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**self.user_data)
    
    def test_user_groups_reverse_accessor(self):
        """Test that the custom related_name for groups works"""
        user = User.objects.create_user(**self.user_data)
        group = Group.objects.create(name='TestGroup')
        user.groups.add(group)
        
        self.assertIn(user, group.custom_user_set.all())
    
    def test_user_permissions_reverse_accessor(self):
        """Test that the custom related_name for permissions works"""
        user = User.objects.create_user(**self.user_data)
        permission = Permission.objects.first()
        user.user_permissions.add(permission)
        
        self.assertIn(user, permission.custom_user_set.all())


class UserAdminTests(TestCase):
    """Test cases for the User admin interface"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        self.dpm_user = User.objects.create_user(
            username='dpmuser',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
    
    def test_list_display_fields(self):
        """Test that list_display contains expected fields"""
        expected_fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
        self.assertEqual(self.admin.list_display, expected_fields)
    
    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields"""
        expected_filters = ('role', 'is_staff', 'is_superuser', 'is_active', 'groups')
        self.assertEqual(self.admin.list_filter, expected_filters)
    
    def test_search_fields(self):
        """Test that search_fields contains expected fields"""
        expected_search = ('username', 'first_name', 'last_name', 'email')
        self.assertEqual(self.admin.search_fields, expected_search)
    
    def test_fieldsets_structure(self):
        """Test that fieldsets are properly structured"""
        fieldsets = self.admin.fieldsets
        self.assertIsInstance(fieldsets, tuple)
        self.assertGreater(len(fieldsets), 0)
        
        # Check that role field is in the fieldsets
        found_role = False
        for name, options in fieldsets:
            if 'fields' in options:
                if 'role' in options['fields']:
                    found_role = True
                    break
        self.assertTrue(found_role, "Role field not found in fieldsets")
    
    def test_add_fieldsets_structure(self):
        """Test that add_fieldsets are properly structured for user creation"""
        add_fieldsets = self.admin.add_fieldsets
        self.assertIsInstance(add_fieldsets, tuple)
        self.assertGreater(len(add_fieldsets), 0)


class UserAuthenticationTests(TestCase):
    """Test cases for user authentication functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.team_member = User.objects.create_user(
            username='teammember',
            email='team@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
    
    def test_team_member_login(self):
        """Test that team members can log in"""
        logged_in = self.client.login(username='teammember', password='testpass123')
        self.assertTrue(logged_in)
    
    def test_dpm_login(self):
        """Test that DPMs can log in"""
        logged_in = self.client.login(username='dpm', password='testpass123')
        self.assertTrue(logged_in)
    
    def test_invalid_login(self):
        """Test that invalid credentials fail login"""
        logged_in = self.client.login(username='teammember', password='wrongpassword')
        self.assertFalse(logged_in)
    
    def test_dpm_has_admin_access(self):
        """Test that DPM users have admin access"""
        self.assertTrue(self.dpm.is_staff)
        self.assertTrue(self.dpm.is_superuser)
        self.assertTrue(self.dpm.has_perm('admin.can_access_admin'))
    
    def test_team_member_no_admin_access(self):
        """Test that team members don't have admin access"""
        self.assertFalse(self.team_member.is_staff)
        self.assertFalse(self.team_member.is_superuser)
    
    def test_user_can_change_password(self):
        """Test that users can change their password"""
        self.client.login(username='teammember', password='testpass123')
        
        # User should be able to authenticate with new password after change
        self.team_member.set_password('newpassword123')
        self.team_member.save()
        
        # Login with old password should fail
        self.client.logout()
        logged_in = self.client.login(username='teammember', password='testpass123')
        self.assertFalse(logged_in)
        
        # Login with new password should succeed
        logged_in = self.client.login(username='teammember', password='newpassword123')
        self.assertTrue(logged_in)


class UserQueryTests(TestCase):
    """Test cases for querying users"""
    
    def setUp(self):
        """Set up test data"""
        self.team_members = []
        self.dpms = []
        
        for i in range(3):
            team_member = User.objects.create_user(
                username=f'teammember{i}',
                email=f'team{i}@example.com',
                password='testpass123',
                role='TEAM_MEMBER'
            )
            self.team_members.append(team_member)
            
            dpm = User.objects.create_user(
                username=f'dpm{i}',
                email=f'dpm{i}@example.com',
                password='testpass123',
                role='DPM'
            )
            self.dpms.append(dpm)
    
    def test_filter_by_role(self):
        """Test filtering users by role"""
        team_members = User.objects.filter(role='TEAM_MEMBER')
        dpms = User.objects.filter(role='DPM')
        
        self.assertEqual(team_members.count(), 3)
        self.assertEqual(dpms.count(), 3)
    
    def test_filter_staff_users(self):
        """Test filtering staff users (should be all DPMs)"""
        staff_users = User.objects.filter(is_staff=True)
        self.assertEqual(staff_users.count(), 3)
        
        # All staff users should be DPMs
        for user in staff_users:
            self.assertEqual(user.role, 'DPM')
    
    def test_filter_active_users(self):
        """Test filtering active users"""
        # Deactivate one user
        self.team_members[0].is_active = False
        self.team_members[0].save()
        
        active_users = User.objects.filter(is_active=True)
        inactive_users = User.objects.filter(is_active=False)
        
        self.assertEqual(active_users.count(), 5)  # 2 team members + 3 DPMs
        self.assertEqual(inactive_users.count(), 1)
    
    def test_order_by_username(self):
        """Test ordering users by username"""
        users = User.objects.all().order_by('username')
        usernames = [user.username for user in users]
        
        self.assertEqual(usernames, sorted(usernames))
    
    def test_search_by_email(self):
        """Test searching users by email"""
        user = User.objects.filter(email__icontains='team0@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'teammember0')


class UserValidationTests(TestCase):
    """Test cases for user validation"""
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        # Username is required
        with self.assertRaises(TypeError):
            User.objects.create_user(
                email='test@example.com',
                password='testpass123',
                role='TEAM_MEMBER'
            )
    
    def test_role_field_required(self):
        """Test that role field is required for custom user"""
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpass123')
        
        with self.assertRaises(ValidationError):
            user.full_clean()
    
    def test_email_format_validation(self):
        """Test email format validation"""
        user = User(
            username='testuser',
            email='invalid-email',
            role='TEAM_MEMBER'
        )
        user.set_password('testpass123')
        
        with self.assertRaises(ValidationError):
            user.full_clean()
    
    def test_username_max_length(self):
        """Test username max length validation"""
        long_username = 'a' * 151  # Django default max_length is 150
        user = User(
            username=long_username,
            email='test@example.com',
            role='TEAM_MEMBER'
        )
        user.set_password('testpass123')
        
        with self.assertRaises(ValidationError):
            user.full_clean()
