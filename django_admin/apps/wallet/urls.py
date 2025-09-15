from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet

router = DefaultRouter()
router.register('wallets', WalletViewSet)

urlpatterns = [
    path('', include(router.urls)),
]