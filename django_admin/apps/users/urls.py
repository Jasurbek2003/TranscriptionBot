from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TelegramUserViewSet

router = DefaultRouter()
router.register("users", TelegramUserViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
