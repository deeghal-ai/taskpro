#!/usr/bin/env python
"""
EMERGENCY: Restore user roles after they were accidentally cleared.
Run with: python restore_user_roles.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from accounts.models import User

def restore_user_roles():
    """Restore roles based on known usernames"""
    print("🚨 EMERGENCY: Restoring user roles...\n")
    
    # Known team members (from our original script)
    team_member_usernames = [
        'shubham',      # Shubham Goyal  
        'gagan',        # Gagan Kumar
        'vishal',       # Vishal Chaudhary
        'shubhamc',     # Shubham Chauhan
        'raju',         # Raju Thapa
        'jagdamba',     # Jagdamba Prasad Yadav
        'garima',       # Garima
        'savita',       # Savita Bhatia
        'vikas',        # Vikas
        'dheeraj',      # Dheeraj Sharma
        'alok',         # Alok Bisht
        'khushboo',     # Khushboo
        'akshay',       # Akshay Kumar
        'piyush',       # Piyush
        'tripti',       # Tripti
        'praveen',      # Existing user
        'saket'         # Existing user
    ]
    
    # Known DPMs
    dpm_usernames = [
        'anil',         # Anil Raghuwanshi
        'jagadish',     # Jagadish Kumar  
        'abhiudaya',    # Abhiudaya Parihar
        'deepti'        # Existing DPM (if exists)
    ]
    
    restored_team = 0
    restored_dpm = 0
    
    print("👥 RESTORING TEAM MEMBER ROLES:")
    for username in team_member_usernames:
        try:
            user = User.objects.get(username=username)
            if not user.role or user.role != 'TEAM_MEMBER':
                user.role = 'TEAM_MEMBER'
                user.save()
                print(f"✅ Restored: {user.first_name} {user.last_name} → TEAM_MEMBER")
                restored_team += 1
            else:
                print(f"✅ Already correct: {user.first_name} {user.last_name}")
        except User.DoesNotExist:
            print(f"⚠️  User not found: {username}")
    
    print(f"\n👨‍💼 RESTORING DPM ROLES:")
    for username in dpm_usernames:
        try:
            user = User.objects.get(username=username)
            if not user.role or user.role != 'DPM':
                user.role = 'DPM'
                user.save()
                print(f"✅ Restored: {user.first_name} {user.last_name} → DPM")
                restored_dpm += 1
            else:
                print(f"✅ Already correct: {user.first_name} {user.last_name}")
        except User.DoesNotExist:
            print(f"⚠️  User not found: {username}")
    
    # Check for any users with missing roles
    print(f"\n🔍 CHECKING FOR USERS WITH MISSING ROLES:")
    users_without_roles = User.objects.filter(role__isnull=True) | User.objects.filter(role='')
    
    if users_without_roles.exists():
        print("⚠️  Users still missing roles:")
        for user in users_without_roles:
            print(f"   • {user.username} ({user.first_name} {user.last_name})")
            # Try to guess based on name patterns
            if user.username in ['admin', 'superuser', 'root']:
                user.role = 'DPM'
                user.save()
                print(f"     → Auto-assigned DPM role")
                restored_dpm += 1
            else:
                # Default to team member
                user.role = 'TEAM_MEMBER' 
                user.save()
                print(f"     → Auto-assigned TEAM_MEMBER role")
                restored_team += 1
    else:
        print("✅ All users have roles assigned")
    
    print(f"\n📊 RESTORATION SUMMARY:")
    print(f"Team Members restored: {restored_team}")
    print(f"DPMs restored: {restored_dpm}")
    print(f"Total restorations: {restored_team + restored_dpm}")
    
    return restored_team + restored_dpm

def show_final_status():
    """Show the final status after restoration"""
    print(f"\n📋 FINAL USER STATUS:")
    print("=" * 50)
    
    team_members = User.objects.filter(role='TEAM_MEMBER').order_by('first_name')
    dpms = User.objects.filter(role='DPM').order_by('first_name') 
    others = User.objects.exclude(role__in=['TEAM_MEMBER', 'DPM']).order_by('first_name')
    
    print(f"👥 TEAM MEMBERS ({team_members.count()}):")
    for user in team_members:
        print(f"   • {user.first_name} {user.last_name} (username: {user.username})")
    
    print(f"\n👨‍💼 DPMs ({dpms.count()}):")
    for user in dpms:
        print(f"   • {user.first_name} {user.last_name} (username: {user.username})")
    
    if others.exists():
        print(f"\n👤 OTHERS ({others.count()}):")
        for user in others:
            print(f"   • {user.first_name} {user.last_name} (username: {user.username}, role: '{user.role}')")
    
    print(f"\n📊 TOTALS:")
    print(f"Team Members: {team_members.count()}")
    print(f"DPMs: {dpms.count()}")
    print(f"Others: {others.count()}")
    print(f"Total Users: {User.objects.count()}")

def main():
    print("🚨 EMERGENCY ROLE RESTORATION\n")
    
    # Restore roles
    restored_count = restore_user_roles()
    
    print("\n" + "="*60 + "\n")
    
    # Show final status
    show_final_status()
    
    if restored_count > 0:
        print(f"\n✅ Successfully restored {restored_count} user roles!")
        print("🎯 Team overview report should now work correctly!")
    else:
        print(f"\n✅ All roles were already correct!")

if __name__ == "__main__":
    main() 