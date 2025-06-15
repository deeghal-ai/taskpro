#!/usr/bin/env python
"""
Script to add real team members and DPMs to the TaskPro database.
Run with: python add_real_users.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from accounts.models import User
from django.contrib.auth.hashers import make_password

def generate_unique_username(first_name, last_name):
    """Generate a unique username, handling duplicates"""
    base_username = first_name.lower()
    
    # If base username is available, use it
    if not User.objects.filter(username=base_username).exists():
        return base_username
    
    # If duplicate, try with last name initial
    if last_name:
        username_with_initial = base_username + last_name[0].lower()
        if not User.objects.filter(username=username_with_initial).exists():
            return username_with_initial
    
    # If still duplicate, add numbers
    counter = 1
    while User.objects.filter(username=f"{base_username}{counter}").exists():
        counter += 1
    
    return f"{base_username}{counter}"

def create_user(first_name, last_name, role):
    """Create a user with the specified pattern"""
    username = generate_unique_username(first_name, last_name)
    password = username + username  # username twice
    
    try:
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email='',  # Keep blank as requested
            role=role,
            password=make_password(password),  # Hash the password
            is_active=True
        )
        print(f"✅ Created {role}: {first_name} {last_name} (username: {username}, password: {password})")
        return user
    except Exception as e:
        print(f"❌ Error creating user {first_name} {last_name}: {e}")
        return None

def main():
    print("🚀 Adding real users to TaskPro database...\n")
    
    # Team Members
    print("👥 ADDING TEAM MEMBERS:")
    team_members = [
        ("Shubham", "Goyal"),
        ("Gagan", "Kumar"), 
        ("Vishal", "Chaudhary"),
        ("Shubham", "Chauhan"),  # This will get username "shubhamc" 
        ("Raju", "Thapa"),
        ("Jagdamba", "Prasad Yadav"),
        ("Garima", ""),
        ("Savita", "Bhatia"),
        ("Vikas", ""),
        ("Dheeraj", "Sharma"),
        ("Alok", "Bisht"),
        ("Khushboo", ""),
        ("Akshay", "Kumar"),
        ("Piyush", ""),
        ("Tripti", "")
    ]
    
    created_team_members = 0
    for first_name, last_name in team_members:
        user = create_user(first_name, last_name, 'Team Member')
        if user:
            created_team_members += 1
    
    print(f"\n📊 Created {created_team_members} team members")
    
    # DPMs
    print("\n👨‍💼 ADDING DPMs:")
    dpms = [
        ("Anil", "Raghuwanshi"),
        ("Jagadish", "Kumar"),
        ("Abhiudaya", "Parihar")
    ]
    
    created_dpms = 0
    for first_name, last_name in dpms:
        user = create_user(first_name, last_name, 'DPM')
        if user:
            created_dpms += 1
    
    print(f"\n📊 Created {created_dpms} DPMs")
    
    # Summary
    print(f"\n🎉 SUMMARY:")
    print(f"Total Team Members: {User.objects.filter(role='Team Member').count()}")
    print(f"Total DPMs: {User.objects.filter(role='DPM').count()}")
    print(f"Total Users: {User.objects.count()}")
    
    print(f"\n📋 LOGIN CREDENTIALS:")
    print(f"Most users: Username = [firstname lowercase], Password = [username twice]")
    print(f"For duplicates: Username = [firstname + last initial], Password = [username twice]")
    print(f"\nExamples:")
    print(f"Gagan Kumar → Username: 'gagan', Password: 'gagangagan'")
    print(f"Shubham Goyal → Username: 'shubham', Password: 'shubhamshubham'")
    print(f"Shubham Chauhan → Username: 'shubhamc', Password: 'shubhamcshubhamc'")

if __name__ == "__main__":
    main() 