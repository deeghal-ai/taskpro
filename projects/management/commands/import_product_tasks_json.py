from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from projects.models import Product, ProductTask
import json
import os

class Command(BaseCommand):
    help = 'Imports product tasks from a JSON file where keys are product names and values are lists of task names.'

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
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing product tasks before importing new ones'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        json_file_path = options['json_file']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']

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

        self.stdout.write(self.style.SUCCESS(f'🚀 Starting to import product tasks from {json_file_path}...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        tasks_created = 0
        tasks_skipped = 0
        products_found = 0
        products_not_found = []

        # Clear existing tasks if requested
        if clear_existing and not dry_run:
            existing_count = ProductTask.objects.count()
            ProductTask.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {existing_count} existing product tasks'))

        for product_name, task_list in data.items():
            if not isinstance(task_list, list):
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Skipping '{product_name}': value must be a list of task names")
                )
                continue

            # Try to find the product by exact name match first
            try:
                product_obj = Product.objects.get(name=product_name)
                products_found += 1
                self.stdout.write(f"\n📦 Processing product: {product_obj.name}")
            except Product.DoesNotExist:
                # Try with underscores replaced by spaces
                try:
                    product_obj = Product.objects.get(name=product_name.replace("_", " "))
                    products_found += 1
                    self.stdout.write(f"\n📦 Processing product: {product_obj.name} (matched with spaces)")
                except Product.DoesNotExist:
                    # Try with spaces replaced by underscores
                    try:
                        product_obj = Product.objects.get(name=product_name.replace(" ", "_"))
                        products_found += 1
                        self.stdout.write(f"\n📦 Processing product: {product_obj.name} (matched with underscores)")
                    except Product.DoesNotExist:
                        products_not_found.append(product_name)
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠️  Product '{product_name}' not found. Skipping.")
                        )
                        continue

            # Process tasks for this product
            for task_name in task_list:
                # Clean up the task name
                cleaned_task_name = str(task_name).strip()
                if not cleaned_task_name:
                    continue

                if dry_run:
                    # Check if task already exists
                    exists = ProductTask.objects.filter(
                        product=product_obj,
                        name=cleaned_task_name
                    ).exists()
                    if exists:
                        self.stdout.write(f"  ➡️  Would skip (exists): '{cleaned_task_name}'")
                        tasks_skipped += 1
                    else:
                        self.stdout.write(f"  ✅ Would create: '{cleaned_task_name}'")
                        tasks_created += 1
                else:
                    # Actually create the task
                    task, created = ProductTask.objects.get_or_create(
                        product=product_obj,
                        name=cleaned_task_name,
                        defaults={
                            'description': f'Imported from JSON file: {os.path.basename(json_file_path)}',
                            'is_active': True
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Created: '{cleaned_task_name}'"))
                        tasks_created += 1
                    else:
                        self.stdout.write(f"  ➡️  Skipped (exists): '{cleaned_task_name}'")
                        tasks_skipped += 1

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('📊 IMPORT SUMMARY'))
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
            self.stdout.write(self.style.WARNING('\n🔍 This was a dry run. Run without --dry-run to actually import the data.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Import complete!')) 