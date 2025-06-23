from django.core.management.base import BaseCommand
from projects.models import Product, ProductTask

class Command(BaseCommand):
    help = 'Verifies the imported product tasks data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Verifying Product Tasks Import...'))
        
        # Get all products with their task counts
        products = Product.objects.all()
        
        total_tasks = 0
        for product in products:
            task_count = ProductTask.objects.filter(product=product).count()
            total_tasks += task_count
            
            if task_count > 0:
                self.stdout.write(f"📦 {product.name}: {task_count} tasks")
                
                # Show first few tasks as sample
                sample_tasks = ProductTask.objects.filter(product=product)[:5]
                for task in sample_tasks:
                    self.stdout.write(f"   - {task.name}")
                if task_count > 5:
                    self.stdout.write(f"   ... and {task_count - 5} more")
                self.stdout.write("")
        
        self.stdout.write(self.style.SUCCESS(f'📊 Total Product Tasks in database: {total_tasks}'))
        
        # Show recently created tasks
        recent_tasks = ProductTask.objects.order_by('-created_at')[:10]
        self.stdout.write(self.style.SUCCESS('\n🕒 Most recently created tasks:'))
        for task in recent_tasks:
            self.stdout.write(f"   - {task.product.name}: {task.name} (created: {task.created_at})") 