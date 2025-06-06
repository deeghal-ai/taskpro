# projects/report_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count, Q
from accounts.models import User
from .models import TeamMemberMetrics, ProjectDelivery
from .services import ReportingService
from datetime import date, timedelta
import json
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404, redirect  # Add redirect


@login_required
def team_member_report(request, team_member_id=None):
    """View for team member productivity report"""
    # Default to current user if team member
    if not team_member_id and request.user.role == 'TEAM_MEMBER':
        team_member = request.user
    else:
        team_member = get_object_or_404(User, id=team_member_id)
    
    # Get date range from request or default to last 30 days
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=30))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Calculate metrics for any missing dates
    current_date = start_date
    while current_date <= end_date:
        ReportingService.calculate_team_member_metrics(team_member, current_date)
        current_date += timedelta(days=1)
    
    # Get report data
    report_data = ReportingService.get_team_member_report(
        team_member, start_date, end_date
    )
    
    context = {
        'team_member': team_member,
        'report': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': f'Productivity Report - {team_member.get_full_name()}'
    }
    
    return render(request, 'projects/reports/team_member_report.html', context)

@login_required
def team_overview_report(request):
    """Overview report for all team members (DPM view)"""
    if request.user.role != 'DPM':
        return redirect('projects:team_member_report')
    
    # Get date range
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=30))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Get all team members
    team_members = User.objects.filter(role='TEAM_MEMBER')
    
    # Build overview data
    overview_data = []
    for member in team_members:
        metrics = TeamMemberMetrics.objects.filter(
            team_member=member,
            date__range=[start_date, end_date]
        ).aggregate(
            avg_productivity=Avg('productivity_score'),
            avg_utilization=Avg('utilization_score'),
            avg_quality=Avg('average_quality_rating'),
            avg_delivery=Avg('average_delivery_rating'),
            total_assignments=Sum('assignments_completed'),
            total_projects=Sum('projects_delivered')
        )
        
        overview_data.append({
            'team_member': member,
            'metrics': metrics
        })
    
    # Sort by productivity
    overview_data.sort(
        key=lambda x: x['metrics']['avg_productivity'] or 0, 
        reverse=True
    )
    
    context = {
        'overview_data': overview_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Team Overview Report'
    }
    
    return render(request, 'projects/reports/team_overview.html', context)

@login_required
def delivery_performance_report(request):
    """Delivery performance report for project incharges"""
    if request.user.role != 'DPM':
        return redirect('home')
    
    # Get date range
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=90))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Get delivery data
    deliveries = ProjectDelivery.objects.filter(
        delivery_date__range=[start_date, end_date]
    ).select_related('project', 'project_incharge')
    
    # Group by project incharge
    incharge_data = {}
    for delivery in deliveries:
        incharge = delivery.project_incharge
        if incharge not in incharge_data:
            incharge_data[incharge] = {
                'deliveries': [],
                'total': 0,
                'on_time': 0,
                'rating_sum': 0,
                'rating_count': 0
            }
        
        incharge_data[incharge]['deliveries'].append(delivery)
        incharge_data[incharge]['total'] += 1
        
        if delivery.days_variance <= 0:
            incharge_data[incharge]['on_time'] += 1
        
        if delivery.delivery_performance_rating:
            incharge_data[incharge]['rating_sum'] += delivery.delivery_performance_rating
            incharge_data[incharge]['rating_count'] += 1
    
    # Calculate averages
    report_data = []
    for incharge, data in incharge_data.items():
        avg_rating = (data['rating_sum'] / data['rating_count']) if data['rating_count'] > 0 else None
        on_time_rate = (data['on_time'] / data['total'] * 100) if data['total'] > 0 else 0
        
        report_data.append({
            'team_member': incharge,
            'average_rating': avg_rating,
            'total_deliveries': data['total'],
            'on_time_rate': on_time_rate,
            'recent_deliveries': sorted(data['deliveries'], key=lambda x: x.delivery_date, reverse=True)[:5]
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