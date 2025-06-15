#!/usr/bin/env python
"""
Script to remove duplicate users from TaskPro database.
Keeps the first occurrence and removes duplicates.
Run with: python remove_duplicate_users.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from accounts.models import User
from collections import defaultdict

def find_and_remove_duplicates():
    """Find and remove duplicate users based on first_name + last_name"""
    print("🔍 Finding duplicate users...\n")
    
    # Group users by first_name + last_name combination
    user_groups = defaultdict(list)
    
    for user in User.objects.all().order_by('date_joined'):
        key = (user.first_name.lower(), user.last_name.lower())
        user_groups[key].append(user)
    
    # Find groups with duplicates
    duplicates_found = False
    total_deleted = 0
    
    for (first_name, last_name), users in user_groups.items():
        if len(users) > 1:
            duplicates_found = True
            print(f"🔄 Found {len(users)} users named '{users[0].first_name} {users[0].last_name}':")
            
            # Keep the first one (oldest by date_joined)
            keeper = users[0]
            print(f"   ✅ KEEPING: {keeper.username} (ID: {keeper.id}, Created: {keeper.date_joined})")
            
            # Delete the rest
            for duplicate in users[1:]:
                print(f"   ❌ DELETING: {duplicate.username} (ID: {duplicate.id}, Created: {duplicate.date_joined})")
                duplicate.delete()
                total_deleted += 1
            
            print()
    
    if not duplicates_found:
        print("✅ No duplicate users found!")
    else:
        print(f"🗑️  Deleted {total_deleted} duplicate users")
    
    return total_deleted

def show_current_users():
    """Show current users in the system"""
    print("📋 CURRENT USERS IN SYSTEM:")
    print("=" * 50)
    
    team_members = User.objects.filter(role='Team Member').order_by('first_name')
    dpms = User.objects.filter(role='DPM').order_by('first_name')
    others = User.objects.exclude(role__in=['Team Member', 'DPM']).order_by('first_name')
    
    if team_members.exists():
        print("👥 TEAM MEMBERS:")
        for user in team_members:
            print(f"   • {user.first_name} {user.last_name} (username: {user.username})")
        print()
    
    if dpms.exists():
        print("👨‍💼 DPMs:")
        for user in dpms:
            print(f"   • {user.first_name} {user.last_name} (username: {user.username})")
        print()
    
    if others.exists():
        print("👤 OTHER USERS:")
        for user in others:
            print(f"   • {user.first_name} {user.last_name} (username: {user.username}, role: {user.role})")
        print()
    
    print(f"📊 SUMMARY:")
    print(f"Total Team Members: {team_members.count()}")
    print(f"Total DPMs: {dpms.count()}")
    print(f"Total Other Users: {others.count()}")
    print(f"Total Users: {User.objects.count()}")

def main():
    print("🧹 Cleaning up duplicate users in TaskPro database...\n")
    
    # Show current state
    print("BEFORE CLEANUP:")
    show_current_users()
    print("\n" + "="*50 + "\n")
    
    # Remove duplicates
    deleted_count = find_and_remove_duplicates()
    
    print("="*50 + "\n")
    
    # Show final state
    print("AFTER CLEANUP:")
    show_current_users()
    
    if deleted_count > 0:
        print(f"\n✅ Successfully removed {deleted_count} duplicate users!")
    else:
        print(f"\n✅ No cleanup needed - no duplicates found!")

if __name__ == "__main__":
    main() 