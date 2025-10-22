from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TranscriptionViewSet

router = DefaultRouter()
router.register("transcriptions", TranscriptionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
