from django.core.management.base import BaseCommand
from projects.models import Product


class Command(BaseCommand):
    help = 'Add products with TAT values (only creates new ones, preserves existing)'

    def handle(self, *args, **options):
        # List of products to add: (name, expected_tat_days)
        # Using 30 days as default TAT for products without specified values
        products_data = [
            ('Real_Apartment_Digitour', 21),
            ('Real_Construction_Digitour', 25),
            ('Real_Villa_Digitour', 21),
            ('Virtual_Full_Project_Digitour', 40),
            ('Walkthrough', 72),
            ('Virtual_Apartment_Digitour', 25),
            ('Virtual_Villa_Digitour', 30),
            ('Virtual_Apartment_Dollhouse', 40),
            ('Augmented_Reality', 45),
            ('Short_Video', 15),
            ('Digiplot', 25),
            ('2D_Floor_Plan', 7),
            ('Profile_Video', 30),  # Default TAT
            ('Digilite', 30),  # Default TAT
            ('PT_Virtual_Tour', 30),  # Default TAT
            ('Real_Full_Project_Digitour', 25),
            ('Virtual_Villa_Dollhouse', 45),
            ('RenderViews_StillImages', 21),
            ('Slice_View', 45),
            ('Rework', 30),  # Default TAT
            ('Custom_Content', 30),  # Default TAT
            ('3d/2d_Floor_plan', 7),
            ('Real_Location_Digitour', 30),
            ('Additional VO', 12),
            ('Virtual_Villa_Full_Project_Digitour', 40),
        ]

        created_count = 0
        skipped_count = 0
        total_existing = Product.objects.count()
        
        self.stdout.write(f'Found {total_existing} existing products')
        
        # Get existing product names for quick lookup
        existing_names = set(
            Product.objects.values_list('name', flat=True)
        )
        
        for name, expected_tat in products_data:
            # Skip empty names
            if not name.strip():
                continue
                
            # Only create if name doesn't exist
            if name in existing_names:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Already exists (skipped): {name}')
                )
            else:
                # Create new product
                Product.objects.create(
                    name=name,
                    expected_tat=expected_tat,
                    is_active=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {name} (TAT: {expected_tat} days)')
                )

        final_total = Product.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Summary ===\n'
                f'Existing products preserved: {skipped_count}\n'
                f'New products created: {created_count}\n'
                f'Total products before: {total_existing}\n'
                f'Total products after: {final_total}\n'
                f'All existing products have been preserved!'
            )
        ) 