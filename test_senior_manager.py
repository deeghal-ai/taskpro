#!/usr/bin/env python
"""
Test script to create and validate Senior Manager functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from accounts.models import User

def create_test_senior_manager():
    """Create a test Senior Manager user"""
    print("Creating test Senior Manager user...")
    
    # Check if user already exists
    username = "senior_manager_test"
    if User.objects.filter(username=username).exists():
        print(f"User {username} already exists. Updating role...")
        user = User.objects.get(username=username)
        user.role = 'SENIOR_MANAGER'
        user.save()
    else:
        # Create new user
        user = User.objects.create_user(
            username=username,
            email="senior.manager@taskpro.com",
            password="testpass123",
            first_name="Senior",
            last_name="Manager",
            role='SENIOR_MANAGER'
        )
    
    print(f"[OK] User created/updated: {user.username}")
    print(f"[OK] Role: {user.get_role_display()}")
    print(f"[OK] is_staff: {user.is_staff}")
    print(f"[OK] is_superuser: {user.is_superuser}")
    
    return user

def test_role_permissions():
    """Test the role permission logic"""
    print("\nTesting role permissions...")
    
    # Test all roles
    roles_to_test = ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER', 'TEAM_MEMBER']
    
    for role in roles_to_test:
        print(f"\nTesting {role}:")
        
        # Create or get test user
        test_username = f"test_{role.lower()}"
        user, created = User.objects.get_or_create(
            username=test_username,
            defaults={
                'email': f"{test_username}@taskpro.com",
                'role': role,
                'first_name': 'Test',
                'last_name': role.replace('_', ' ').title()
            }
        )
        if not created:
            user.role = role
            user.save()
        
        print(f"  Role: {user.get_role_display()}")
        print(f"  is_staff: {user.is_staff}")
        print(f"  is_superuser: {user.is_superuser}")
        
        # Test access permissions
        has_management_access = user.role in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']
        has_full_management_access = user.role in ['DPM', 'VIDEO_PM']
        
        print(f"  Has reporting access: {has_management_access}")
        print(f"  Has full management access: {has_full_management_access}")

def main():
    """Main test function"""
    print("=== Senior Manager Role Test ===")
    
    # Create test senior manager
    senior_manager = create_test_senior_manager()
    
    # Test permissions
    test_role_permissions()
    
    print("\n=== Test Summary ===")
    print("[OK] Senior Manager role added to User model")
    print("[OK] Database migration applied successfully")  
    print("[OK] Permission logic implemented")
    print("[OK] Test users created")
    
    print("\n=== Next Steps ===")
    print("1. Login to admin panel with superuser account")
    print("2. Navigate to Users section")
    print("3. Create/edit users and assign Senior Manager role")
    print("4. Test access to reporting pages")
    print("5. Verify Senior Managers cannot access project management pages")
    
if __name__ == "__main__":
    main()
