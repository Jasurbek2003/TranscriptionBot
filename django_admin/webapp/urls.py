# django_admin/webapp/urls.py

from django.urls import path
from . import views

app_name = 'webapp'

urlpatterns = [
    # Pages
    path('', views.home, name='home'),
    path('auth/', views.auth_with_token, name='auth'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_page, name='upload'),
    path('transcriptions/', views.transcriptions_page, name='transcriptions'),
    path('logout/', views.user_logout, name='logout'),

    # API endpoints
    path('api/auth/status/', views.auth_status, name='auth_status'),
    path('api/upload/', views.upload_file, name='api_upload'),
]
