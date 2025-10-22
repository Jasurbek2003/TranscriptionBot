"""
Sentry configuration for error monitoring and performance tracking.

To enable Sentry:
1. Sign up at https://sentry.io
2. Create a new Django project
3. Add SENTRY_DSN to your .env file
4. Set SENTRY_ENABLED=true in .env

Environment variables:
- SENTRY_DSN: Your Sentry project DSN
- SENTRY_ENABLED: Enable/disable Sentry (default: False in dev, True in production)
- SENTRY_ENVIRONMENT: Environment name (development, staging, production)
- SENTRY_TRACES_SAMPLE_RATE: Percentage of transactions to sample (0.0 to 1.0)
- SENTRY_PROFILES_SAMPLE_RATE: Percentage of transactions to profile (0.0 to 1.0)
"""

import logging
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration

logger = logging.getLogger(__name__)


def init_sentry(debug=False):
    """
    Initialize Sentry SDK with appropriate configuration.

    Args:
        debug: Whether Django is in DEBUG mode
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    sentry_enabled = os.getenv("SENTRY_ENABLED", "false").lower() == "true"

    # Auto-enable Sentry in production if DSN is provided
    if not debug and sentry_dsn:
        sentry_enabled = True

    if not sentry_enabled:
        logger.info("Sentry monitoring is disabled")
        return

    if not sentry_dsn:
        logger.warning("SENTRY_DSN not configured. Sentry monitoring disabled.")
        return

    # Get environment configuration
    environment = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    # Configure logging integration
    # Send ERROR and above to Sentry
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors and above as events
    )

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            # Integrations
            integrations=[
                DjangoIntegration(
                    transaction_style="url",
                    middleware_spans=True,
                    signals_spans=True,
                    cache_spans=True,
                ),
                RedisIntegration(),
                CeleryIntegration(),
                sentry_logging,
            ],
            # Performance monitoring
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            # Additional options
            send_default_pii=False,  # Don't send personally identifiable information
            attach_stacktrace=True,
            request_bodies="medium",  # Include request bodies (small, medium, always)
            # Set release version
            release=os.getenv("SENTRY_RELEASE", None),
            # Before send hook - filter sensitive data
            before_send=before_send_handler,
        )

        logger.info(f"Sentry initialized successfully for environment: {environment}")
        logger.info(f"Traces sample rate: {traces_sample_rate * 100}%")
        logger.info(f"Profiles sample rate: {profiles_sample_rate * 100}%")

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_handler(event, hint):
    """
    Filter and modify events before sending to Sentry.
    Use this to remove sensitive data or filter out certain errors.
    """
    # Filter out certain exceptions
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Ignore specific exceptions
        ignored_exceptions = [
            "django.http.UnreadablePostError",
            "django.core.exceptions.DisallowedHost",
        ]

        if any(exc_type.__name__ in ignored for ignored in ignored_exceptions):
            return None

    # Remove sensitive data from request
    if "request" in event:
        # Remove sensitive headers
        sensitive_headers = ["authorization", "x-api-key", "cookie"]
        if "headers" in event["request"]:
            for header in sensitive_headers:
                if header in event["request"]["headers"]:
                    event["request"]["headers"][header] = "[Filtered]"

        # Remove sensitive POST data
        if "data" in event["request"]:
            sensitive_fields = ["password", "secret", "token", "api_key", "credit_card"]
            for field in sensitive_fields:
                if field in event["request"]["data"]:
                    event["request"]["data"][field] = "[Filtered]"

    return event


def capture_message(message, level="info", **kwargs):
    """
    Manually capture a message in Sentry.

    Args:
        message: The message to capture
        level: Message level (info, warning, error, fatal)
        **kwargs: Additional context data
    """
    if sentry_sdk.Hub.current.client:
        sentry_sdk.capture_message(message, level=level, **kwargs)
    else:
        logger.log(getattr(logging, level.upper()), message)


def capture_exception(exception=None, **kwargs):
    """
    Manually capture an exception in Sentry.

    Args:
        exception: The exception to capture (if None, captures current exception)
        **kwargs: Additional context data
    """
    if sentry_sdk.Hub.current.client:
        sentry_sdk.capture_exception(exception, **kwargs)
    else:
        logger.exception("Exception occurred" if exception is None else str(exception))


def set_user_context(user):
    """
    Set user context for Sentry events.

    Args:
        user: Django user object
    """
    if sentry_sdk.Hub.current.client:
        sentry_sdk.set_user(
            {
                "id": user.id,
                "username": getattr(user, "username", None),
                "telegram_id": getattr(user, "telegram_id", None),
            }
        )


def set_context(key, value):
    """
    Set custom context for Sentry events.

    Args:
        key: Context key
        value: Context value (dict)
    """
    if sentry_sdk.Hub.current.client:
        sentry_sdk.set_context(key, value)


def add_breadcrumb(message, category="default", level="info", data=None):
    """
    Add a breadcrumb to track user actions.

    Args:
        message: Breadcrumb message
        category: Category (e.g., 'payment', 'transcription', 'auth')
        level: Level (debug, info, warning, error, fatal)
        data: Additional data dict
    """
    if sentry_sdk.Hub.current.client:
        sentry_sdk.add_breadcrumb(message=message, category=category, level=level, data=data or {})
