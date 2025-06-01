# Then create a new file: projects/report_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import ReportingService
from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from accounts.models import User

@login_required
def team_member_report(request, team_member_id=None):
    """View for team member productivity report"""
    # Default to current user if team member
    if not team_member_id and request.user.role == 'TEAM_MEMBER':
        team_member = request.user
    else:
        team_member = get_object_or_404(User, id=team_member_id)
    
    # Get date range from request or default to last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    report_data = ReportingService.get_team_member_report(
        team_member, start_date, end_date
    )
    
    context = {
        'team_member': team_member,
        'report': report_data,
        'title': f'Productivity Report - {team_member.get_full_name()}'
    }
    
    return render(request, 'projects/reports/team_member_report.html', context)


@login_required
def delivery_performance_report(request):
    """
    View for delivery performance across all project incharges.
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=90)  # Last 3 months
    
    # Get all team members who have been project incharge
    team_members_with_deliveries = User.objects.filter(
        project_deliveries__delivery_date__range=[start_date, end_date]
    ).distinct()
    
    # Build report data
    report_data = []
    for member in team_members_with_deliveries:
        deliveries = ProjectDelivery.objects.filter(
            project_incharge=member,
            delivery_date__range=[start_date, end_date]
        )
        
        metrics = deliveries.aggregate(
            avg_rating=Avg('delivery_performance_rating'),
            total_projects=Count('id'),
            on_time=Count('id', filter=Q(days_variance__lte=0)),
            late=Count('id', filter=Q(days_variance__gt=0))
        )
        
        report_data.append({
            'team_member': member,
            'average_rating': metrics['avg_rating'],
            'total_deliveries': metrics['total_projects'],
            'on_time_rate': (metrics['on_time'] / metrics['total_projects'] * 100) if metrics['total_projects'] > 0 else 0,
            'deliveries': deliveries[:5]  # Recent 5
        })
    
    # Sort by average rating
    report_data.sort(key=lambda x: x['average_rating'] or 0, reverse=True)
    
    context = {
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Delivery Performance Report'
    }
    
    return render(request, 'projects/reports/delivery_performance.html', context)