# projects/report_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count, Q
from accounts.models import User
from .models import ProjectDelivery
from .services import ReportingService
from datetime import date, timedelta
import json
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404, redirect  # Add redirect


@login_required
def team_member_report(request, team_member_id=None):
    """View for team member productivity report - now using on-demand calculations"""
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
    
    # Get report data (now calculated on-demand!)
    metrics = ReportingService.get_team_member_metrics(team_member, start_date, end_date)
    
    # Get delivery history for details
    delivery_history = ProjectDelivery.objects.filter(
        project_incharge=team_member,
        delivery_date__range=[start_date, end_date]
    ).order_by('-delivery_date')
    
    # Prepare context in the format expected by template
    report_data = {
        'period': metrics['period'],
        'delivery_history': delivery_history,
        'summary': {
            'average_productivity': metrics['productivity']['score'],
            'average_optimization': metrics['optimization']['score'],
            'average_utilization': metrics['utilization']['score'],
            'average_efficiency': metrics['efficiency']['score'],
            'average_quality_rating': metrics['quality']['average_rating'],
            'average_delivery_rating': metrics['delivery']['average_rating'],
            'total_assignments_completed': metrics['quality']['total_assignments'],
            'total_projects_delivered': metrics['delivery']['total_projects'],
            'on_time_delivery_rate': metrics['delivery']['on_time_rate'],
            'total_hours_projected': metrics['productivity']['projected_hours'],
            'total_hours_worked': metrics['productivity']['worked_hours'],
            'optimization_saved_hours': metrics['optimization']['saved_hours'],
            'efficiency_total_work_hours': metrics['efficiency']['total_work_minutes'] / 60 if metrics['efficiency']['total_work_minutes'] else 0,
            'efficiency_misc_hours': metrics['efficiency']['misc_minutes'] / 60 if metrics['efficiency']['misc_minutes'] else 0,
        }
    }
    
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
    """Overview report for all team members (DPM view) - now using on-demand calculations"""
    if request.user.role != 'DPM':
        return redirect('projects:team_member_report')
    
    # Get date range
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=30))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Get overview data (much simpler now!)
    overview_data = ReportingService.get_team_overview(start_date, end_date)
    
    # Transform data format to match template expectations
    formatted_overview = []
    for item in overview_data:
        formatted_overview.append({
            'team_member': item['team_member'],
            'metrics': {
                'avg_productivity': item['metrics']['productivity']['score'],
                'avg_optimization': item['metrics']['optimization']['score'],
                'avg_utilization': item['metrics']['utilization']['score'],
                'avg_efficiency': item['metrics']['efficiency']['score'],
                'avg_quality': item['metrics']['quality']['average_rating'],
                'avg_delivery': item['metrics']['delivery']['average_rating'],
                'total_assignments': item['metrics']['quality']['total_assignments'],
                'total_projects': item['metrics']['delivery']['total_projects']
            }
        })
    
    # Calculate team averages and totals
    team_averages = {}
    team_totals = {'total_assignments': 0, 'total_projects': 0}
    
    if formatted_overview:
        # Calculate averages for each metric
        metrics_to_average = ['avg_productivity', 'avg_optimization', 'avg_utilization', 'avg_efficiency', 'avg_quality', 'avg_delivery']
        for metric in metrics_to_average:
            values = [item['metrics'][metric] for item in formatted_overview if item['metrics'][metric] is not None]
            team_averages[metric] = sum(values) / len(values) if values else None
        
        # Calculate totals
        team_totals['total_assignments'] = sum(item['metrics']['total_assignments'] or 0 for item in formatted_overview)
        team_totals['total_projects'] = sum(item['metrics']['total_projects'] or 0 for item in formatted_overview)
    
    context = {
        'overview_data': formatted_overview,
        'team_averages': team_averages,
        'team_totals': team_totals,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Team Overview Report'
    }
    
    return render(request, 'projects/reports/team_overview.html', context)

@login_required
def delivery_performance_report(request):
    """Delivery performance report for project incharges - simplified"""
    if request.user.role != 'DPM':
        return redirect('home')
    
    # Get date range
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=90))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Get delivery data - much simpler without complex stored metrics
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
        
        # Calculate on-time using the actual database fields, not the property
        if (delivery.expected_completion_date and 
            delivery.actual_completion_date <= delivery.expected_completion_date):
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