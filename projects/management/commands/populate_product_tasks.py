from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Product, ProductTask

class Command(BaseCommand):
    help = 'Populates the ProductTask model with a predefined set of tasks for each product.'

    # --- Data provided by the user ---
    TASK_DATA = {
        "Virtual_Apartment_Digitour": {
            "columnI": ["1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex/villa", "2.5 BHK Duplex/villa", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Link Creation", "Changes", "4k Updation", "Data Check", "Improvement"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "Null"]
        },
        "Virtual_Villa_Digitour": {
            "columnI": ["2 BHK Duplex/ Villa", "2.5 BHK Duplex/ Villa", "3.5 BHK Duplex/ Villa", "3 BHK Duplex/ Villa", "4 BHK Dulpex/ Villa", "4.5 BHK Duplex/ Villa", "5 BHK Duplex/ Villa", "5.5 BHK Duplex/ Villa", "Link Creation", "Changes", "4k Updation", "Data Check", "Improvement"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "Null"]
        },
        "Virtual_Full_Project_Digitour": {
            "columnI": ["Tower Modeling", "Master Plan Modeling & Texturing", "Gate Modeling & Texturing", "Boundary Wall Modeling & Texturing", "Podium Modeling & Texturing", "Terrace Modeling & Texturing", "Basement Parking Modeling & Texturing", "Master Plan Landscaping", "Podium Landscaping", "Terrace Landscaping", "Outer Development", "Day Aerial View", "Night Aerial View", "Camera Points Placement", "Club House Modeling Texturing", "Link Creation", "Zumba", "Yoga And Exercise Deck", "Kitty Party Area Indoor ", "Hangout Space", "Co-Working Space", "Cafe Reception", "Sport Lounge", "Indoor Games Areas", "Social Lounge", "Terrace Garden Sitting", "Mocktail Bar", "Gym And Yoga Zone", "Guest Bedroom", "Party Lawn Interior", "Toddler Pods Interior", "Indoor Lounge", "Banquet Hall", "Office Area", "Multipurpose Activity Room", "Conference Room", "Lounge Area", "Library", "Locker Room", "Reception Area", "Entrance Lobby Interior", "Amphitheatre", "Open Gym", "Kids Play Area", "Outdoor Game Area", "Entrance Plaza", "Waterbody", "Security Pad", "Bi-Cycle Parking", "Outdoor Reading Pod", "Community Court", "Toddlers Play Area", "Pets Corner", "Private Court", "Board Games Area", "Terraces Seating", "Sunken Garden", " Courtyard", "Pool Area", "Cabana Area", "Mutilpuroise Area", "Outdoor Gym", "Hammock Area", "Yoga / Meditation Area", "Skywalk Bridge", "Senior Citizen ", "Outdoor Work Station", "Reading Pod", "Bon Fire Area", "Cricket Net ", "Golf Area Mini", "Outdoor Lounge Area", "Clubhouse Outdoor Area", "Pond Area", "File Merging", "File Rectification ", "Link Update 4K", "Tower Draft Renders", "Element modeling and placement ", "Prop Modeling", "Interior Amneities", "Exterior Amneities", "Tower Proxy Creation", "Custom Content Task", "Interior Machine Hours", "Exterior Machine Hours", "Villa & Small Tower Modeling", "1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex/villa", "2.5 BHK Duplex/villa", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Spa", "Business Centre", "Cards Room", "Theatre", "Aerobics", "Creche", "Society Office", "Changes"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "C1", "C2", "C3", "C4", "Null"]
        },
        "Walkthrough": {
            "columnI": ["Tower Modeling", "Master Plan Modeling & Texturing", "Gate Modeling Texturing", "Boundary Wall Modeling & Texturing", "Podium Modeling & Texturing", "Terrace Modeling & Texturing", "Basement Parking Modeling & Texturing", "Master Plan Landscaping", "Podium Landscaping", "Terrace Landscaping", "Outer Development", "Day Aerial View", "Night Aerial View", "Day  Lighting", "Night  Lighting", "Site Modeling & Texturing", "Camera Preview Compositing", "Club House Modeling Texturing", "Camera Animation ", "Exterior People Passes", "Interior People Passes ", "Single Car Animation", "Traffic Simulation", "Water Simulation", "Post Production Still", "Post Production Video", "Logo Animation ", "Lower Thirds/ Naming", "Logo Search", "Logo R&D / Tutorial", "Map Search", "Map R&D / Tutorial", "Map Animation", "Render Rectification ", "Zumba", "Yoga And Exercise Deck", "Kitty Party Area Indoor ", "Hangout Space", "Co-Working Space", "Cafe Reception", "Sport Lounge", "Indoor Games Areas", "Social Lounge", "Terrace Garden Sitting", "Mocktail Bar", "Gym And Yoga Zone", "Guest Bedroom", "Party Lawn Interior", "Toddler Pods Interior", "Indoor Lounge", "Banquet Hall", "Office Area", "Multipurpose Activity Room", "Conference Room", "Lounge Area", "Library", "Locker Room", "Reception Area", "Entrance Lobby Interior", "Amphitheatre", "Open Gym", "Kids Play Area", "Outdoor Game Area", "Entrance Plaza", "Waterbody", "Security Pad", "Bi-Cycle Parking", "Outdoor Reading Pod", "Community Court", "Toddlers Play Area", "Kids Play Area", "Pets Corner", "Private Court", "Board Games Area", "Terraces Seating", "Sunken Garden", " Courtyard", "Pool Area", "Cabana Area", "Multipurpose area", "Outdoor Gym", "Hammock Area", "Yoga / Meditation Area", "Skywalk Bridge", "Senior Citizen ", "Outdoor Work Station", "Reading Pod", "Bon Fire Area", "Cricket Net ", "Golf Area Mini", "Outdoor Lounge Area", "Clubhouse Outdoor Area", "Pond Area", "File merging", "File Rectification ", "Link Update 4K", "Tower Draft Renders", "Element modeling and placement ", "Prop modeling", "Interior Amneities", "Exterior Amneities", "Tower Proxy creation", "Camera View / Nth Rendering", "Villa & Small Tower Modeling", "1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex/villa", "2.5 BHK Duplex/villa", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Meeting Room ", "Lift Lobby", "Business Center", "Theater / Auditorium", "Render Pass", "Changes", "Voice Over", "Camera on server"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "C1", "C2", "C3", "C4", "Null"]
        },
        "Virtual_Apartment_Dollhouse": {
            "columnI": ["1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex", "2.5 BHK Duplex", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Link creation", "Changes", "4k Updation", "Improvement", "Data check"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "Null"]
        },
        "Virtual_Villa_Dollhouse": {
            "columnI": ["2 BHK Duplex/ Villa", "2.5 BHK Duplex/ Villa", "3.5 BHK Duplex/ Villa", "3 BHK Duplex/ Villa", "4 BHK Dulpex/ Villa", "4.5 BHK Duplex/ Villa", "5 BHK Duplex/ Villa", "5.5 BHK Duplex/ Villa", "Link creation", "Changes", "4k Updation", "Data check", "Improvement"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "C1", "C2", "C3", "C4", "Null"]
        },
        "Real_Apartment_Digitour": {
            "columnI": ["1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex/villa", "2.5 BHK Duplex/villa", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Link Creation", "Post Production ", "Stitching & Pano Creation", "Construction Digitour"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Null"]
        },
        "Real_Villa_Digitour": {
            "columnI": ["1 RK", "1 BHK", "1.5 BHK", "2 BHK", "2.5 BHK", "3 BHK", "3.5 BHK", "4 BHK", "4.5 BHK", "5 BHK", "5.5 BHK", "2 BHK Duplex/villa", "2.5 BHK Duplex/villa", "3.5 BHK Duplex", "3 BHK Duplex", "4 BHK Dulpex", "4.5 BHK Duplex", "5 BHK Duplex", "5.5 BHK Duplex", "Link Creation", "Post Production ", "Stitching & Pano Creation", "Construction Digitour"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Null"]
        },
        "Real_Full_Project_Digitour": {
            "columnI": ["Ext. Amenities", "Int. Amenities", "Apt/ Vill Interior", "Masterplan", "Outer", "Tower", "Link Creation", "Post Production ", "Stitching & Pano Creation", "Construction Digitour"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Null"]
        },
        "Digiplot": {
            "columnI": ["100 M Overlay", "50 M Overlay", "50ft Overlay", "Plot no. & Sq.ft. PS", "Pano2vr", "Hotspot Creation", "Link Creation"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "Null"]
        },
        "Profile_Video": {
            "columnI": ["Provide Video Creation", "Provide Video Edit", "Provide Video Upload"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "Null"]
        },
        "Short_Video": {
            "columnI": ["Short Video Creation", "Short Video Edit"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "Null"]
        },
        "RenderViews_StillImages": {
            "columnI": ["Draft Camera Angle", "Post Production", "Day Lighting and Adjustment", "Night Lighting and Adjustment", "Camera Views", "Night Lighting"],
            "columnJ": ["Q1", "Q2", "Q3", "Q4", "Q5", "Null"]
        },
    }

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting to populate product tasks...'))
        
        tasks_created = 0
        tasks_skipped = 0

        for product_name, tasks in self.TASK_DATA.items():
            try:
                # Find the product by its name. Replace underscores with spaces for matching.
                product_obj = Product.objects.get(name=product_name.replace("_", " "))
                self.stdout.write(f"\nProcessing product: {product_obj.name}")

                all_task_names = tasks['columnI'] + tasks['columnJ']
                
                for task_name in all_task_names:
                    # Clean up the task name
                    cleaned_task_name = task_name.strip()
                    if not cleaned_task_name:
                        continue

                    task, created = ProductTask.objects.get_or_create(
                        product=product_obj,
                        name=cleaned_task_name
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Created task: '{cleaned_task_name}'"))
                        tasks_created += 1
                    else:
                        tasks_skipped += 1

            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  ⚠️  Product '{product_name.replace('_', ' ')}' not found. Skipping."))
                continue

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Population complete! Created: {tasks_created}, Skipped (already existed): {tasks_skipped}'))