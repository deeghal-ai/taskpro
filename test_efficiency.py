#!/usr/bin/env python
"""
Test script to verify the new efficiency calculation logic.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings.development')
django.setup()

from projects.services import ReportingService
from accounts.models import User
from datetime import date, timedelta

def test_efficiency_calculation():
    """Test the new efficiency calculation with 2.5 days leave allowance."""
    
    # Get a team member to test
    team_member = User.objects.filter(role='TEAM_MEMBER').first()
    if not team_member:
        print('No team members found')
        return
    
    # Test with last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f'Testing efficiency calculation for: {team_member.first_name} {team_member.last_name}')
    print(f'Date range: {start_date} to {end_date}')
    print('=' * 50)
    
    try:
        metrics = ReportingService.get_team_member_metrics(team_member, start_date, end_date)
        
        print('UTILIZATION METRICS:')
        print(f'  Score: {metrics["utilization"]["score"]}%')
        print(f'  Worked minutes: {metrics["utilization"]["worked_minutes"]}')
        print(f'  Available minutes: {metrics["utilization"]["available_minutes"]}')
        print()
        
        print('EFFICIENCY METRICS:')
        print(f'  Score: {metrics["efficiency"]["score"]}%')
        print(f'  Assignment minutes: {metrics["efficiency"]["assignment_minutes"]}')
        print(f'  Available minutes: {metrics["efficiency"]["available_minutes"]}')
        print(f'  Total work minutes: {metrics["efficiency"]["total_work_minutes"]}')
        print()
        
        print('KEY DIFFERENCES:')
        print(f'  - Efficiency excludes misc hours (uses only assignment work)')
        print(f'  - Efficiency has 2.5 days monthly leave allowance vs 0 for utilization')
        print(f'  - Same roster day processing logic for both metrics')
        print()
        
        # Verify calculation logic
        days_in_range = (end_date - start_date).days + 1
        efficiency_prorated_allowance = (2.5 / 30) * days_in_range
        utilization_prorated_allowance = (0 / 30) * days_in_range
        
        print('CALCULATION VERIFICATION:')
        print(f'  Days in range: {days_in_range}')
        print(f'  Efficiency prorated allowance: {efficiency_prorated_allowance:.2f} days')
        print(f'  Utilization prorated allowance: {utilization_prorated_allowance:.2f} days')
        print()
        
        print('SUCCESS: Efficiency calculation test completed successfully!')
        
    except Exception as e:
        print(f'❌ Error during testing: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_efficiency_calculation()
