"""
URL Configuration for Youtomation App
"""
from django.urls import path
from . import views

app_name = 'youtomation_app'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Videos
    path('videos/', views.videos_list, name='videos_list'),
    path('videos/<int:video_id>/', views.video_detail, name='video_detail'),
    
    # Statistics
    path('statistics/', views.statistics, name='statistics'),
    
    # API endpoints
    path('api/video/<int:video_id>/status/', views.video_status_api, name='video_status_api'),
    path('api/video/<int:video_id>/logs/', views.video_logs_api, name='video_logs_api'),
    path('api/trending-topics/', views.trending_topics_api, name='trending_topics_api'),
]
