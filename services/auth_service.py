"""Authentication service for one-time tokens using Django ORM"""

import os
import secrets
# Import Django models
import sys
from datetime import timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.utils import timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "django_admin"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django

django.setup()

from webapp.models import OneTimeToken

from apps.users.models import TelegramUser


class AuthService:
    """Service for managing one-time authentication tokens using Django ORM"""

    @sync_to_async
    def generate_token(
            self, user: TelegramUser, purpose: str = "general_access", expires_in_hours: int = 1
    ) -> OneTimeToken:
        """
        Generate a new one-time token for a user

        Args:
            user: TelegramUser instance
            purpose: Purpose of the token (e.g., 'large_file_upload')
            expires_in_hours: Token expiration time in hours

        Returns:
            OneTimeToken instance
        """
        # Generate a secure random token
        token_value = secrets.token_urlsafe(32)

        # Calculate expiration time
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)

        # Create token record
        token = OneTimeToken.objects.create(
            user=user, token=token_value, purpose=purpose, expires_at=expires_at
        )

        return token

    @sync_to_async
    def validate_token(
            self, token_value: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[TelegramUser]:
        """
        Validate a one-time token and return the associated user

        Args:
            token_value: The token string
            ip_address: Optional IP address of the request
            user_agent: Optional user agent string

        Returns:
            TelegramUser if valid, None otherwise
        """
        try:
            # Find token
            token = OneTimeToken.objects.get(token=token_value)

            # Check if token is valid
            if not token.is_valid():
                return None

            # Mark token as used
            token.is_used = True
            token.used_at = timezone.now()
            token.ip_address = ip_address or ""
            token.user_agent = user_agent or ""
            token.save()

            # Get and return user
            return token.user

        except OneTimeToken.DoesNotExist:
            return None

    @sync_to_async
    def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens from database

        Returns:
            Number of deleted tokens
        """
        now = timezone.now()
        expired_tokens = OneTimeToken.objects.filter(expires_at__lt=now)
        count = expired_tokens.count()
        expired_tokens.delete()
        return count

    @sync_to_async
    def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a specific user

        Args:
            user_id: User ID

        Returns:
            Number of revoked tokens
        """
        active_tokens = OneTimeToken.objects.filter(user_id=user_id, is_used=False)
        count = active_tokens.count()

        # Mark all as used
        active_tokens.update(is_used=True, used_at=timezone.now())

        return count
