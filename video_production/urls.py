from django.urls import path
from . import views

app_name = 'video_production'

urlpatterns = [
    # Main project views
    path('', views.video_project_list, name='project_list'),
    path('delivered/', views.video_delivered_projects, name='delivered_projects'),
    path('export/', views.export_pipeline_video_projects, name='export_pipeline_projects'),
    path('create/', views.video_create_project, name='create_project'),
    
    # Project detail and management
    path('<uuid:project_id>/', views.video_project_detail, name='project_detail'),
    path('<uuid:project_id>/edit/', views.video_edit_project, name='edit_project'),
    path('<uuid:project_id>/complete/', views.video_complete_project, name='complete_project'),
    
    # Status management
    path('<uuid:project_id>/update-status/', views.video_update_project_status, name='update_status'),
    
    # Reports
    path('reports/video-report/', views.video_report, name='video_report'),
]