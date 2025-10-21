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
    path('payment/', views.payment_page, name='payment'),
    path('logout/', views.user_logout, name='logout'),

    # API endpoints
    path('api/auth/telegram/', views.telegram_webapp_auth, name='telegram_webapp_auth'),
    path('api/auth/status/', views.auth_status, name='auth_status'),
    path('api/upload/', views.upload_file, name='api_upload'),
    path('api/download/<int:transcription_id>/', views.download_transcription, name='download_transcription'),
    path('api/payment/initiate/', views.initiate_payment, name='initiate_payment'),
]
