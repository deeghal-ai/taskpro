from django.urls import path
from . import views

app_name = 'video_production'

urlpatterns = [
    # Main project views
    path('', views.video_project_list, name='project_list'),
    path('delivered/', views.video_delivered_projects, name='delivered_projects'),
    path('create/', views.video_create_project, name='create_project'),
    
    # Project detail and management
    path('<uuid:project_id>/', views.video_project_detail, name='project_detail'),
    path('<uuid:project_id>/edit/', views.video_edit_project, name='edit_project'),
    path('<uuid:project_id>/complete/', views.video_complete_project, name='complete_project'),
    
    # Status management
    path('<uuid:project_id>/update-status/', views.video_update_project_status, name='update_status'),
    
    # Cut management
    path('<uuid:project_id>/submit-cut/', views.video_submit_cut, name='submit_cut'),
    path('<uuid:project_id>/cut-feedback/<int:cut_number>/', views.video_cut_feedback, name='cut_feedback'),
    
    # Voiceover management
    path('<uuid:project_id>/submit-voiceover/', views.video_submit_voiceover_script, name='submit_voiceover'),
    path('<uuid:project_id>/approve-voiceover/<int:script_version>/', views.video_approve_voiceover_script, name='approve_voiceover'),
] 