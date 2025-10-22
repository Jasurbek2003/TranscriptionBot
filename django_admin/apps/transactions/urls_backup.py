from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TransactionViewSet, click_webhook, payme_webhook

router = DefaultRouter()
router.register("transactions", TransactionViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # Payment gateway webhooks
    path("webhooks/click/", click_webhook, name="click_webhook"),
    path("webhooks/payme/", payme_webhook, name="payme_webhook"),
]
