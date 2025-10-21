from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, click_prepare, click_complete, payme_webhook

router = DefaultRouter()
router.register('transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Payment gateway webhooks
    # Click webhooks - separate endpoints for prepare and complete
    path('webhooks/click/prepare/', click_prepare, name='click_prepare'),
    path('webhooks/click/complete/', click_complete, name='click_complete'),
    # Payme webhook - single endpoint for all JSON-RPC methods
    path('webhooks/payme/', payme_webhook, name='payme_webhook'),
]