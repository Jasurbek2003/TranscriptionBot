from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet

router = DefaultRouter()
router.register('transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]