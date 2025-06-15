#!/usr/bin/env python
"""
Script to check and fix user roles in TaskPro database.
Run with: python check_user_roles.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from accounts.models import User

def check_current_roles():
    """Check what role values currently exist"""
    print("🔍 Checking current user roles...\n")
    
    # Get all unique role values
    roles = User.objects.values_list('role', flat=True).distinct()
    
    print("📋 CURRENT ROLE VALUES:")
    for role in roles:
        count = User.objects.filter(role=role).count()
        print(f"   • '{role}' → {count} users")
    
    print(f"\n📊 Total users: {User.objects.count()}")
    return roles

def show_users_by_role():
    """Show users grouped by their current roles"""
    print("\n👥 USERS BY ROLE:")
    print("=" * 50)
    
    roles = User.objects.values_list('role', flat=True).distinct()
    
    for role in roles:
        users = User.objects.filter(role=role).order_by('first_name')
        print(f"\n🏷️  ROLE: '{role}' ({users.count()} users)")
        for user in users:
            print(f"   • {user.first_name} {user.last_name} (username: {user.username})")

def fix_role_values():
    """Fix role values to match what the code expects"""
    print("\n🔧 FIXING ROLE VALUES...")
    print("=" * 50)
    
    # Fix Team Member roles
    team_member_variations = ['Team Member', 'TEAM_MEMBER', 'team_member', 'TeamMember']
    total_team_fixed = 0
    
    for variation in team_member_variations:
        users = User.objects.filter(role=variation)
        if users.exists():
            count = users.count()
            users.update(role='Team Member')
            print(f"✅ Fixed {count} users from '{variation}' to 'Team Member'")
            total_team_fixed += count
    
    # Fix DPM roles
    dpm_variations = ['DPM', 'dpm', 'Dpm', 'Digital Project Manager']
    total_dpm_fixed = 0
    
    for variation in dpm_variations:
        users = User.objects.filter(role=variation)
        if users.exists():
            count = users.count()
            users.update(role='DPM')
            print(f"✅ Fixed {count} users from '{variation}' to 'DPM'")
            total_dpm_fixed += count
    
    print(f"\n📊 SUMMARY:")
    print(f"Team Member roles fixed: {total_team_fixed}")
    print(f"DPM roles fixed: {total_dpm_fixed}")
    
    return total_team_fixed + total_dpm_fixed

def main():
    print("🔍 Checking and fixing user roles in TaskPro database...\n")
    
    # Show current state
    print("BEFORE FIXES:")
    check_current_roles()
    show_users_by_role()
    
    print("\n" + "="*70 + "\n")
    
    # Fix roles
    fixed_count = fix_role_values()
    
    print("\n" + "="*70 + "\n")
    
    # Show final state
    print("AFTER FIXES:")
    check_current_roles()
    show_users_by_role()
    
    if fixed_count > 0:
        print(f"\n✅ Successfully fixed {fixed_count} user roles!")
        print("🎯 Now the team overview report should show all team members!")
    else:
        print(f"\n✅ No role fixes needed - all roles are already correct!")

if __name__ == "__main__":
    main() 