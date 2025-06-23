from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from projects.models import Product, ProductTask
import json
import os
import traceback

class Command(BaseCommand):
    help = 'Debug version of product tasks import with detailed logging'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing product tasks data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually creating records'
        )

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        dry_run = options['dry_run']

        # Check database connection
        self.stdout.write(f'🔍 Database engine: {connection.settings_dict["ENGINE"]}')
        self.stdout.write(f'🔍 Database name: {connection.settings_dict["NAME"]}')
        
        # Validate file exists
        if not os.path.exists(json_file_path):
            raise CommandError(f'File "{json_file_path}" does not exist.')

        # Load JSON data
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')

        if not isinstance(data, dict):
            raise CommandError('JSON data must be an object/dictionary with product names as keys.')

        self.stdout.write(self.style.SUCCESS(f'🚀 Starting debug import from {json_file_path}...'))
        self.stdout.write(f'📊 JSON contains {len(data)} products')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        # Count existing tasks before import
        initial_count = ProductTask.objects.count()
        self.stdout.write(f'📊 Initial ProductTask count: {initial_count}')

        tasks_created = 0
        tasks_skipped = 0
        products_found = 0
        products_not_found = []
        
        # Check products first
        self.stdout.write('\n🔍 Checking products in database:')
        all_products = Product.objects.all()
        for product in all_products:
            self.stdout.write(f'  - {product.name}')
        
        try:
            if not dry_run:
                # Use savepoint instead of full transaction for better error handling
                with transaction.atomic():
                    self.stdout.write('\n🔄 Starting database transaction...')
                    
                    for product_name, task_list in data.items():
                        self.stdout.write(f'\n📦 Processing: {product_name}')
                        
                        if not isinstance(task_list, list):
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠️  Skipping '{product_name}': value must be a list")
                            )
                            continue

                        # Try to find the product
                        product_obj = None
                        try:
                            product_obj = Product.objects.get(name=product_name)
                            self.stdout.write(f"  ✅ Found product: {product_obj.name}")
                        except Product.DoesNotExist:
                            try:
                                product_obj = Product.objects.get(name=product_name.replace("_", " "))
                                self.stdout.write(f"  ✅ Found product with spaces: {product_obj.name}")
                            except Product.DoesNotExist:
                                try:
                                    product_obj = Product.objects.get(name=product_name.replace(" ", "_"))
                                    self.stdout.write(f"  ✅ Found product with underscores: {product_obj.name}")
                                except Product.DoesNotExist:
                                    products_not_found.append(product_name)
                                    self.stdout.write(f"  ❌ Product not found: {product_name}")
                                    continue

                        if product_obj:
                            products_found += 1
                            self.stdout.write(f"  📝 Processing {len(task_list)} tasks...")
                            
                            for i, task_name in enumerate(task_list):
                                cleaned_task_name = str(task_name).strip()
                                if not cleaned_task_name:
                                    continue
                                
                                try:
                                    task, created = ProductTask.objects.get_or_create(
                                        product=product_obj,
                                        name=cleaned_task_name,
                                        defaults={
                                            'description': f'Imported from JSON: {os.path.basename(json_file_path)}',
                                            'is_active': True
                                        }
                                    )
                                    
                                    if created:
                                        tasks_created += 1
                                        self.stdout.write(f"    ✅ [{i+1:2d}] Created: '{cleaned_task_name}'")
                                    else:
                                        tasks_skipped += 1
                                        self.stdout.write(f"    ➡️  [{i+1:2d}] Exists: '{cleaned_task_name}'")
                                        
                                except Exception as e:
                                    self.stdout.write(f"    ❌ Error creating task '{cleaned_task_name}': {e}")
                                    raise  # Re-raise to trigger rollback
                    
                    # Check count after import but before commit
                    current_count = ProductTask.objects.count()
                    self.stdout.write(f'\n📊 ProductTask count before commit: {current_count}')
                    self.stdout.write('✅ Transaction completed successfully!')
                    
            else:
                # Dry run logic (same as before but without actual creation)
                for product_name, task_list in data.items():
                    if not isinstance(task_list, list):
                        continue
                        
                    try:
                        product_obj = Product.objects.get(name=product_name)
                        products_found += 1
                    except Product.DoesNotExist:
                        try:
                            product_obj = Product.objects.get(name=product_name.replace("_", " "))
                            products_found += 1
                        except Product.DoesNotExist:
                            try:
                                product_obj = Product.objects.get(name=product_name.replace(" ", "_"))
                                products_found += 1
                            except Product.DoesNotExist:
                                products_not_found.append(product_name)
                                continue
                    
                    for task_name in task_list:
                        cleaned_task_name = str(task_name).strip()
                        if not cleaned_task_name:
                            continue
                            
                        exists = ProductTask.objects.filter(
                            product=product_obj,
                            name=cleaned_task_name
                        ).exists()
                        
                        if exists:
                            tasks_skipped += 1
                        else:
                            tasks_created += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during import: {e}'))
            self.stdout.write(self.style.ERROR(f'❌ Traceback: {traceback.format_exc()}'))
            raise

        # Final count check
        if not dry_run:
            final_count = ProductTask.objects.count()
            self.stdout.write(f'\n📊 Final ProductTask count: {final_count}')
            self.stdout.write(f'📊 Net change: +{final_count - initial_count}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('📊 DEBUG IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f"Products found: {products_found}")
        self.stdout.write(f"Products not found: {len(products_not_found)}")
        self.stdout.write(f"Tasks {'would be created' if dry_run else 'created'}: {tasks_created}")
        self.stdout.write(f"Tasks skipped (already existed): {tasks_skipped}")
        
        if products_not_found:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Products not found:"))
            for product in products_not_found:
                self.stdout.write(f"  - {product}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 This was a dry run. Run without --dry-run to actually import.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Debug import complete!')) 