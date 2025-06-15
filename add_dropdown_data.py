#!/usr/bin/env python
"""
Script to add common dropdown data for TaskPro.
Run with: python add_dropdown_data.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from projects.models import Product, ProductSubcategory, ProjectStatusOption
from locations.models import City

def add_products():
    """Add common products"""
    print("📦 ADDING PRODUCTS:")
    
    products_data = [
        ("Website Design", 7),
        ("Mobile App Development", 30),
        ("E-commerce Website", 14),
        ("Logo Design", 3),
        ("Brand Identity", 5),
        ("Digital Marketing", 10),
        ("SEO Optimization", 21),
        ("Content Writing", 7),
        ("Social Media Management", 30),
        ("Graphic Design", 5)
    ]
    
    created = 0
    for name, tat in products_data:
        product, created_obj = Product.objects.get_or_create(
            name=name,
            defaults={'expected_tat': tat, 'is_active': True}
        )
        if created_obj:
            print(f"✅ Created product: {name} (TAT: {tat} days)")
            created += 1
        else:
            print(f"⚠️  Product already exists: {name}")
    
    print(f"📊 Created {created} new products")
    return created

def add_subcategories():
    """Add product subcategories"""
    print("\n🏷️  ADDING PRODUCT SUBCATEGORIES:")
    
    subcategories = [
        "Corporate Website",
        "Personal Portfolio", 
        "E-commerce Platform",
        "Landing Page",
        "Mobile App (iOS)",
        "Mobile App (Android)",
        "Web Application",
        "Static Website",
        "Dynamic Website",
        "Custom Development"
    ]
    
    created = 0
    for name in subcategories:
        subcategory, created_obj = ProductSubcategory.objects.get_or_create(
            name=name,
            defaults={'is_active': True}
        )
        if created_obj:
            print(f"✅ Created subcategory: {name}")
            created += 1
        else:
            print(f"⚠️  Subcategory already exists: {name}")
    
    print(f"📊 Created {created} new subcategories")
    return created

def add_cities():
    """Add common cities"""
    print("\n🏙️  ADDING CITIES:")
    
    cities_data = [
        ("Delhi", "Delhi", "North"),
        ("Mumbai", "Maharashtra", "West"),
        ("Bangalore", "Karnataka", "South"),
        ("Chennai", "Tamil Nadu", "South"),
        ("Hyderabad", "Telangana", "South"),
        ("Kolkata", "West Bengal", "East"),
        ("Pune", "Maharashtra", "West"),
        ("Ahmedabad", "Gujarat", "West"),
        ("Jaipur", "Rajasthan", "North"),
        ("Surat", "Gujarat", "West"),
        ("Lucknow", "Uttar Pradesh", "North"),
        ("Kanpur", "Uttar Pradesh", "North"),
        ("Nagpur", "Maharashtra", "West"),
        ("Indore", "Madhya Pradesh", "Central"),
        ("Bhopal", "Madhya Pradesh", "Central"),
        ("Visakhapatnam", "Andhra Pradesh", "South"),
        ("Patna", "Bihar", "East"),
        ("Vadodara", "Gujarat", "West"),
        ("Ghaziabad", "Uttar Pradesh", "North"),
        ("Ludhiana", "Punjab", "North")
    ]
    
    created = 0
    for name, state, region in cities_data:
        city, created_obj = City.objects.get_or_create(
            name=name,
            defaults={'state': state, 'region': region, 'is_active': True}
        )
        if created_obj:
            print(f"✅ Created city: {name}, {state} ({region})")
            created += 1
        else:
            print(f"⚠️  City already exists: {name}")
    
    print(f"📊 Created {created} new cities")
    return created

def add_project_statuses():
    """Add project status options"""
    print("\n📋 ADDING PROJECT STATUS OPTIONS:")
    
    statuses_data = [
        ("Sales Confirmation", "Awaiting Data", "Not Started", 1),
        ("Data Collection", "In Progress", "Active", 2),
        ("Design Phase", "In Progress", "Active", 3),
        ("Development Phase", "In Progress", "Active", 4),
        ("Testing Phase", "In Progress", "Active", 5),
        ("Client Review", "Awaiting Feedback", "Pending", 6),
        ("Revisions", "In Progress", "Active", 7),
        ("Final Approval", "Awaiting Approval", "Pending", 8),
        ("Final Delivery", "Completed", "Delivered", 9),
        ("Project Completed", "Completed", "Delivered", 10)
    ]
    
    created = 0
    for name, cat1, cat2, order in statuses_data:
        status, created_obj = ProjectStatusOption.objects.get_or_create(
            name=name,
            defaults={
                'category_one': cat1,
                'category_two': cat2,
                'order': order,
                'is_active': True
            }
        )
        if created_obj:
            print(f"✅ Created status: {name} ({cat1} - {cat2})")
            created += 1
        else:
            print(f"⚠️  Status already exists: {name}")
    
    print(f"📊 Created {created} new project statuses")
    return created

def main():
    print("🚀 Adding dropdown data to TaskPro database...\n")
    
    total_created = 0
    total_created += add_products()
    total_created += add_subcategories()
    total_created += add_cities()
    total_created += add_project_statuses()
    
    print(f"\n🎉 SUMMARY:")
    print(f"Total Products: {Product.objects.count()}")
    print(f"Total Subcategories: {ProductSubcategory.objects.count()}")
    print(f"Total Cities: {City.objects.count()}")
    print(f"Total Project Statuses: {ProjectStatusOption.objects.count()}")
    print(f"Total new records created: {total_created}")

if __name__ == "__main__":
    main() 