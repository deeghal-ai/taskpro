# projects/report_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from datetime import date, timedelta
from accounts.models import User
from .services import ReportingService
from .views import ensure_has_management_access
from .models import Project, ProjectDelivery, TaskAssignment
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import json

# Import permission helpers from views
def ensure_has_management_access(request):
    """Check if user has management access (DPM, VIDEO_PM, or SENIOR_MANAGER)"""
    if request.user.role not in ['DPM', 'VIDEO_PM', 'SENIOR_MANAGER']:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('projects:project_list')
    return None

def ensure_has_full_management_access(request):
    """Check if user has full management access (DPM or VIDEO_PM only)"""
    if request.user.role not in ['DPM', 'VIDEO_PM']:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('projects:project_list')
    return None


@login_required
def team_member_report(request, team_member_id=None):
    """View for team member productivity report - now using on-demand calculations"""
    # Check permissions - allow TEAM_MEMBER to view own report, or management roles to view any
    if team_member_id:
        # Viewing another user's report - requires management access
        redirect_response = ensure_has_management_access(request)
        if redirect_response:
            return redirect_response
        team_member = get_object_or_404(User, id=team_member_id)
    elif request.user.role == 'TEAM_MEMBER':
        # Team member viewing own report
        team_member = request.user
    else:
        # Management user without specific team_member_id - redirect to team overview
        return redirect('projects:team_overview_report')
    
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
    """Overview report for all team members (Management view) - now using on-demand calculations"""
    # Check if user has management access (includes Senior Managers)
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
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
    # Check if user has management access (includes Senior Managers)
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
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

@login_required
def lol_report(request):
    """LoL report with date range filter and team member selection"""
    # Check if user has management access (includes Senior Managers)
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
    # Initialize form data
    selected_team_members = []
    report_data = []
    
    # Get date range from request or default to last 30 days
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=30))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    # Get selected team members from POST or GET
    if request.method == 'POST':
        selected_member_ids = request.POST.getlist('team_members')
    else:
        selected_member_ids = request.GET.getlist('team_members')
    
    # Get all team members for the form
    all_team_members = User.objects.filter(role='TEAM_MEMBER').order_by('first_name', 'last_name')
    
    # If team members are selected, generate the report
    if selected_member_ids:
        selected_team_members = User.objects.filter(
            id__in=selected_member_ids,
            role='TEAM_MEMBER'
        )
        
        # Get report data
        report_data = ReportingService.get_lol_report_data(
            selected_team_members,
            start_date,
            end_date
        )
    
    # Prepare team members with selection state for the form
    team_members_with_selection = []
    for member in all_team_members:
        team_members_with_selection.append({
            'member': member,
            'is_selected': str(member.id) in selected_member_ids
        })
    
    context = {
        'team_members': team_members_with_selection,
        'selected_member_ids': selected_member_ids,
        'selected_team_members': selected_team_members,
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'LoL Report',
        'has_results': len(report_data) > 0,
    }
    
    return render(request, 'projects/reports/lol_report.html', context)

@login_required
def reports_dashboard(request):
    """Reports dashboard for Senior Managers and management roles"""
    # Check if user has management access (includes Senior Managers)
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
    # Get some quick stats for the dashboard (optional)
    from accounts.models import User
    from .models import Project, ProjectDelivery
    from datetime import date, timedelta
    
    # Calculate some basic stats
    total_team_members = User.objects.filter(role='TEAM_MEMBER').count()
    
    # Active projects (those not in 'Final Delivery' status)
    active_projects = Project.objects.exclude(
        current_status__category_two='Final Delivery'
    ).count()
    
    # This month's deliveries
    current_month_start = date.today().replace(day=1)
    deliveries_this_month = ProjectDelivery.objects.filter(
        delivery_date__gte=current_month_start
    ).count()
    
    # Calculate average productivity using the same logic as team overview
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    # Get team overview data to calculate average productivity
    overview_data = ReportingService.get_team_overview(start_date, end_date)
    
    # Calculate team average productivity
    avg_productivity = None
    if overview_data:
        productivity_scores = [
            item['metrics']['productivity']['score'] 
            for item in overview_data 
            if item['metrics']['productivity']['score'] is not None
        ]
        if productivity_scores:
            avg_productivity = sum(productivity_scores) / len(productivity_scores)
    
    context = {
        'total_team_members': total_team_members,
        'active_projects': active_projects,
        'deliveries_this_month': deliveries_this_month,
        'avg_productivity': avg_productivity,
        'title': 'Reports Dashboard'
    }
    
    return render(request, 'projects/reports/reports_dashboard.html', context)


@login_required
def lol_report_export_excel(request):
    """Enhanced LoL report Excel export with raw metrics and final overview"""
    # Check if user has management access
    redirect_response = ensure_has_management_access(request)
    if redirect_response:
        return redirect_response
    
    # Get parameters from request
    end_date = request.GET.get('end_date', date.today())
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    start_date = request.GET.get('start_date', end_date - timedelta(days=30))
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    
    selected_member_ids = request.GET.getlist('team_members')
    if not selected_member_ids:
        messages.error(request, "No team members selected for export.")
        return redirect('projects:lol_report')
    
    # Get selected team members and report data
    selected_team_members = User.objects.filter(
        id__in=selected_member_ids,
        role='TEAM_MEMBER'
    )
    
    report_data = ReportingService.get_lol_report_data(
        selected_team_members,
        start_date,
        end_date
    )
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LoL Report"
    
    # Define styles
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    subheader_font = Font(bold=True, size=11)
    subheader_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    center_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(border_style="thin"),
        right=Side(border_style="thin"),
        top=Side(border_style="thin"),
        bottom=Side(border_style="thin")
    )
    
    # Set column widths
    ws.column_dimensions['A'].width = 20  # Name
    ws.column_dimensions['B'].width = 12  # Utilization
    ws.column_dimensions['C'].width = 12  # Productivity  
    ws.column_dimensions['D'].width = 15  # Quality Rating
    ws.column_dimensions['E'].width = 15  # Utilization Worked Hours
    ws.column_dimensions['F'].width = 12  # Available Hours
    ws.column_dimensions['G'].width = 15  # Productivity Worked Hours
    ws.column_dimensions['H'].width = 12  # Projected Hours
    ws.column_dimensions['I'].width = 20  # Individual Ratings
    
    # Overview table columns (starting from column J)
    ws.column_dimensions['J'].width = 20  # Name
    ws.column_dimensions['K'].width = 15  # Project Utilization
    ws.column_dimensions['L'].width = 15  # Productivity
    ws.column_dimensions['M'].width = 15  # Quality Score
    ws.column_dimensions['N'].width = 12  # Quality in %
    ws.column_dimensions['O'].width = 12  # % Total
    ws.column_dimensions['P'].width = 15  # Eligibility Status
    
    # RAW METRICS SECTION (Left side)
    current_row = 1
    
    # Main header for raw metrics
    ws.merge_cells(f'A{current_row}:I{current_row}')
    ws[f'A{current_row}'] = "RAW INDIVIDUAL METRICS"
    ws[f'A{current_row}'].font = Font(bold=True, size=14)
    ws[f'A{current_row}'].alignment = center_alignment
    ws[f'A{current_row}'].fill = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
    current_row += 2
    
    # Raw metrics headers
    raw_headers = [
        "Name", "Utilization %", "Productivity %", "Avg Quality Rating", 
        "Utilization Worked Hours", "Available Hours", "Productivity Worked Hours", "Projected Hours", "Individual Quality Ratings"
    ]
    
    for col_idx, header in enumerate(raw_headers, 1):
        cell = ws.cell(row=current_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = border
    
    current_row += 1
    
    # Raw metrics data
    for data in report_data:
        member = data['team_member']
        
        # Get individual quality ratings as comma-separated string
        individual_ratings = ", ".join([f"{rating:.2f}" for rating in data['quality_ratings_list']]) or "No ratings"
        
        row_data = [
            f"{member.first_name} {member.last_name}",
            f"{data['avg_utilization']:.2f}%",
            f"{data['avg_productivity']:.2f}%",
            f"{data['avg_quality_rating']:.2f}" if data['avg_quality_rating'] else "N/A",
            f"{data['utilization_details']['worked_hours']:.1f}",
            f"{data['utilization_details']['available_hours']:.1f}",
            f"{data['productivity_details']['worked_hours']:.1f}",
            f"{data['productivity_details']['projected_hours']:.1f}",
            individual_ratings
        ]
        
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            cell.border = border
            if col_idx > 1:  # Align numbers to center
                cell.alignment = center_alignment
        
        current_row += 1
    
    # FINAL OVERVIEW SECTION (Right side)
    overview_start_row = 1
    overview_col_start = 10  # Column J
    
    # Main header for overview
    ws.merge_cells(f'J{overview_start_row}:P{overview_start_row}')
    ws[f'J{overview_start_row}'] = "FINAL OVERVIEW TABLE"
    ws[f'J{overview_start_row}'].font = Font(bold=True, size=14)
    ws[f'J{overview_start_row}'].alignment = center_alignment
    ws[f'J{overview_start_row}'].fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    overview_start_row += 2
    
    # Overview headers
    overview_headers = [
        "Name", "Project Utilization - 40% Weightage", "Productivity - 30% Weightage", 
        "Quality Score - 30% Weightage (< number of less mistakes )", "Quality Score in %", 
        "% Total", "Eligibility Status"
    ]
    
    for col_idx, header in enumerate(overview_headers):
        cell = ws.cell(row=overview_start_row, column=overview_col_start + col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = border
    
    overview_start_row += 1
    
    # Overview data
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # Light red for failing criteria
    
    for data in report_data:
        member = data['team_member']
        
        overview_row_data = [
            f"{member.first_name} {member.last_name}",
            f"{data['avg_utilization']:.2f}%",
            f"{data['avg_productivity']:.2f}%",
            f"{data['avg_quality_rating']:.2f}" if data['avg_quality_rating'] else "N/A",
            f"{data['quality_score']:.2f}%",
            f"{data['total_percentage']:.2f}%",
            data['eligibility_status']
        ]
        
        for col_idx, value in enumerate(overview_row_data):
            cell = ws.cell(row=overview_start_row, column=overview_col_start + col_idx, value=value)
            cell.border = border
            
            # Apply red background only to cells that fail criteria
            if col_idx == 1 and data['avg_utilization'] < 85:  # Utilization column
                cell.fill = red_fill
            elif col_idx == 2 and data['avg_productivity'] < 95:  # Productivity column
                cell.fill = red_fill
            elif col_idx == 3 and (data['avg_quality_rating'] is None or data['avg_quality_rating'] < 2.95):  # Quality rating column
                cell.fill = red_fill
            
            if col_idx > 0:  # Align data to center
                cell.alignment = center_alignment
        
        overview_start_row += 1
    
    # Add legend/criteria at the bottom
    legend_row = max(current_row + 3, overview_start_row + 3)
    
    ws.merge_cells(f'A{legend_row}:P{legend_row}')
    ws[f'A{legend_row}'] = "ELIGIBILITY CRITERIA"
    ws[f'A{legend_row}'].font = Font(bold=True, size=12)
    ws[f'A{legend_row}'].alignment = center_alignment
    legend_row += 1
    
    criteria_text = [
        "• Utilization: Must be ≥ 85%",
        "• Productivity: Must be ≥ 95%", 
        "• Quality Rating: Must be ≥ 2.95"
    ]
    
    for criterion in criteria_text:
        ws[f'A{legend_row}'] = criterion
        ws[f'A{legend_row}'].font = Font(bold=True)
        legend_row += 1
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"lol_report_{start_date}_{end_date}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response