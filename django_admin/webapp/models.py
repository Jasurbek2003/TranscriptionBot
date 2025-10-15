# django_admin/webapp/models.py

from django.db import models
from django.utils import timezone
from datetime import datetime
from apps.users.models import TelegramUser


class OneTimeToken(models.Model):
    """One-time sign-in token for web access"""

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='one_time_tokens'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)

    # Token details
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    # IP and User Agent tracking
    ip_address = models.CharField(max_length=45, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')

    # Purpose of token (e.g., 'large_file_upload', 'general_access')
    purpose = models.CharField(max_length=50, default='general_access')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'one_time_tokens'
        verbose_name = 'One-Time Token'
        verbose_name_plural = 'One-Time Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Token for {self.user} - {'used' if self.is_used else 'active'}"

    def is_valid(self):
        """Check if token is valid"""
        if self.is_used:
            return False

        # Handle both timezone-aware and timezone-naive datetimes
        now = timezone.now()
        expires = self.expires_at

        # Make timezone-aware if needed
        if expires and timezone.is_naive(expires):
            expires = timezone.make_aware(expires)

        if now > expires:
            return False
        return True

    def mark_as_used(self, ip=None, user_agent=None):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        if ip:
            self.ip_address = ip
        if user_agent:
            self.user_agent = user_agent
        self.save()
