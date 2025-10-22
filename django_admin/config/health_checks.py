"""Health check endpoints for monitoring and load balancers."""

import logging
import sys

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 if the application is running.

    Use this for simple liveness probes.
    """
    return JsonResponse(
        {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": getattr(settings, "VERSION", "0.1.0"),
        }
    )


def ready_check(request):
    """
    Readiness check endpoint.
    Verifies that the application is ready to serve traffic.

    Checks:
    - Database connectivity
    - Cache connectivity (Redis)

    Returns 200 if ready, 503 if not ready.
    Use this for readiness probes in Kubernetes/load balancers.
    """
    checks = {"database": False, "cache": False, "overall": False}

    status_code = 200

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = False
        checks["database_error"] = str(e)
        status_code = 503

    # Check cache connection (Redis)
    try:
        cache.set("health_check", "ok", timeout=10)
        result = cache.get("health_check")
        checks["cache"] = result == "ok"
        if not checks["cache"]:
            raise ValueError("Cache value mismatch")
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks["cache"] = False
        checks["cache_error"] = str(e)
        status_code = 503

    # Overall status
    checks["overall"] = checks["database"] and checks["cache"]

    response_data = {
        "status": "ready" if checks["overall"] else "not_ready",
        "timestamp": timezone.now().isoformat(),
        "checks": checks,
        "version": getattr(settings, "VERSION", "0.1.0"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    return JsonResponse(response_data, status=status_code)


def detailed_status(request):
    """
    Detailed status endpoint for monitoring systems.

    Provides detailed information about:
    - Application version
    - Database status
    - Cache status
    - Environment
    - Python version

    This endpoint should be restricted to admin users in production.
    """
    # Check if user is authenticated and is staff
    if not settings.DEBUG:
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse(
                {"error": "Unauthorized", "message": "This endpoint requires admin authentication"},
                status=403,
            )

    checks = {}

    # Database check with details
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = {
                "status": "healthy",
                "engine": settings.DATABASES["default"]["ENGINE"],
                "name": settings.DATABASES["default"]["NAME"],
            }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Cache check with details
    try:
        cache.set("health_check_detailed", "ok", timeout=10)
        result = cache.get("health_check_detailed")
        if result == "ok":
            checks["cache"] = {
                "status": "healthy",
                "backend": settings.CACHES["default"]["BACKEND"],
            }
        else:
            raise ValueError("Cache value mismatch")
    except Exception as e:
        checks["cache"] = {"status": "unhealthy", "error": str(e)}

    # Application info
    app_info = {
        "version": getattr(settings, "VERSION", "0.1.0"),
        "debug": settings.DEBUG,
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "django_version": (
            settings.DJANGO_VERSION if hasattr(settings, "DJANGO_VERSION") else "unknown"
        ),
    }

    return JsonResponse(
        {
            "status": "operational",
            "timestamp": timezone.now().isoformat(),
            "application": app_info,
            "checks": checks,
        }
    )
