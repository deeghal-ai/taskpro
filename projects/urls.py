#projects/urls.py
from django.urls import path
from . import views
from . import views, report_views

app_name = 'projects'

urlpatterns = [
    # Project Management URLs
    path('', views.project_list, name='project_list'),
    path('delivered/', views.delivered_projects, name='delivered_projects'),
    path('create/', views.create_project, name='create_project'),
    path('<uuid:project_id>/', views.project_detail, name='project_detail'),
    path('<uuid:project_id>/update-status/', views.update_project_status, name='update_project_status'),
    
    # Task Management URLs
    path('tasks/dashboard/', views.dpm_task_dashboard, name='dpm_task_dashboard'),
    path('<uuid:project_id>/manage/', views.project_management, name='project_management'),
    path('<uuid:project_id>/update-configuration/', views.update_project_configuration, name='update_project_configuration'),
    path('<uuid:project_id>/create-task/', views.create_project_task, name='create_project_task'),

    # Individual task detail and management
    path(
        '<uuid:project_id>/tasks/<uuid:task_id>/',
        views.task_detail,
        name='task_detail'
    ),
    path(
        '<uuid:project_id>/tasks/<uuid:task_id>/create-assignment/',
        views.create_task_assignment,
        name='create_task_assignment'
    ),
    path(
        '<uuid:project_id>/tasks/<uuid:task_id>/update-assignment/<uuid:assignment_id>/',
        views.update_task_assignment,
        name='update_task_assignment'
    ),
    path(
        '<uuid:project_id>/tasks/<uuid:task_id>/rate-assignment/<uuid:assignment_id>/',
        views.update_quality_rating,
        name='update_quality_rating'
    ),
    # Team member URLs
    path('tasks/my-assignments/', views.team_member_dashboard, name='team_member_dashboard'),
    path('my-projects/', views.my_projects, name='my_projects'), 
    path('assignments/<uuid:assignment_id>/timesheet/', views.assignment_timesheet, name='assignment_timesheet'),
    path('daily-roster/', views.daily_roster, name='daily_roster'),
    path('roster/', views.monthly_roster, name='roster'), 
    path('roster/<int:year>/<int:month>/', views.monthly_roster, name='roster_date'),
    path('roster/update-day/', views.update_roster_day, name='update_roster_day'),
    
    # API endpoints
    path('api/cities/', views.get_cities, name='api_cities'),
    # Reporting URLs
    path('reports/my-report/', report_views.team_member_report, name='my_report'),
    path('reports/team-member/<uuid:team_member_id>/', report_views.team_member_report, name='team_member_report'),
    path('reports/team-overview/', report_views.team_overview_report, name='team_overview_report'),
    path('reports/delivery-performance/', report_views.delivery_performance_report, name='delivery_performance_report'),
    
]