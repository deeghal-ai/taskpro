from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.services import ProjectService
import json


class Command(BaseCommand):
    help = 'Analyze time between Project Start Date and 1st Cut Delivery for projects from Feb 1st, 2025'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='table',
            choices=['table', 'json', 'csv'],
            help='Output format (table, json, or csv)'
        )
        parser.add_argument(
            '--details',
            action='store_true',
            help='Include individual project details in output'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting project timeline analysis...'))
        
        try:
            # Run the analysis
            results = ProjectService.analyze_project_start_to_first_cut_timeline()
            
            # Display summary
            summary = results['summary']
            self.stdout.write(f"\n=== Analysis Summary ===")
            self.stdout.write(f"Analysis Date From: {summary['analysis_date_from']}")
            self.stdout.write(f"Total Projects Analyzed: {summary['total_projects_analyzed']}")
            self.stdout.write(f"Products Analyzed: {summary['products_analyzed']}")
            
            # Display results based on format
            if options['format'] == 'json':
                self.output_json(results, options['details'])
            elif options['format'] == 'csv':
                self.output_csv(results, options['details'])
            else:
                self.output_table(results, options['details'])
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during analysis: {str(e)}')
            )
            raise

    def output_table(self, results, include_details=False):
        """Output results in table format"""
        product_averages = results['product_averages']
        
        if not product_averages:
            self.stdout.write(self.style.WARNING("\nNo data found for the specified criteria."))
            return
            
        self.stdout.write(f"\n=== Product-wise Average Timeline ===")
        self.stdout.write(f"{'Product':<30} {'Avg Days':<10} {'Projects':<10} {'Total Qty':<10}")
        self.stdout.write("-" * 70)
        
        for item in product_averages:
            self.stdout.write(
                f"{item['product']:<30} "
                f"{item['average_days']:<10} "
                f"{item['project_count']:<10} "
                f"{item['total_quantity']:<10}"
            )
        
        if include_details:
            self.stdout.write(f"\n=== Individual Project Details ===")
            individual_projects = results['individual_projects']
            
            if individual_projects:
                self.stdout.write(f"{'HS_ID':<8} {'Product':<20} {'Start Date':<12} {'1st Cut Date':<12} {'Days':<6}")
                self.stdout.write("-" * 70)
                
                for project in individual_projects:
                    self.stdout.write(
                        f"{project['hs_id']:<8} "
                        f"{project['product'][:19]:<20} "
                        f"{project['start_date']:<12} "
                        f"{project['first_cut_date']:<12} "
                        f"{project['days_taken']:<6}"
                    )

    def output_json(self, results, include_details=False):
        """Output results in JSON format"""
        output_data = {
            'summary': results['summary'],
            'product_averages': results['product_averages']
        }
        
        if include_details:
            output_data['individual_projects'] = results['individual_projects']
        
        self.stdout.write(json.dumps(output_data, indent=2, default=str))

    def output_csv(self, results, include_details=False):
        """Output results in CSV format"""
        import csv
        import sys
        
        # Product averages CSV
        self.stdout.write("=== Product Averages CSV ===")
        self.stdout.write("Product,Average Days,Project Count,Total Quantity")
        
        for item in results['product_averages']:
            self.stdout.write(f"{item['product']},{item['average_days']},{item['project_count']},{item['total_quantity']}")
        
        if include_details:
            self.stdout.write("\n=== Individual Projects CSV ===")
            self.stdout.write("HS_ID,Project Name,Product,Start Date,1st Cut Date,Days Taken,Quantity")
            
            for project in results['individual_projects']:
                self.stdout.write(
                    f"{project['hs_id']},{project['project_name']},{project['product']},"
                    f"{project['start_date']},{project['first_cut_date']},{project['days_taken']},{project['quantity']}"
                )
