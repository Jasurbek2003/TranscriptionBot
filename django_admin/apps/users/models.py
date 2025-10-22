from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.enums import Language, UserRole, UserStatus


class TelegramUser(AbstractUser):
    """Custom user model for Telegram users"""

    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name=_("Telegram ID"),
        help_text=_("Unique Telegram identifier for the user"),
        null=True,
        blank=True,
    )
    telegram_username = models.CharField(
        max_length=255, blank=True, null=True, db_index=True, verbose_name=_("Telegram Username")
    )
    first_name = models.CharField(max_length=255, verbose_name=_("First Name"))
    last_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Last Name")
    )
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, db_index=True, verbose_name=_("Phone Number")
    )
    language_code = models.CharField(
        max_length=10,
        choices=[(lang.value, lang.name) for lang in Language],
        default=Language.EN.value,
        verbose_name=_("Language"),
    )
    role = models.CharField(
        max_length=20,
        choices=[(role.value, role.name) for role in UserRole],
        default=UserRole.USER.value,
        verbose_name=_("Role"),
    )
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.name) for status in UserStatus],
        default=UserStatus.ACTIVE.value,
        verbose_name=_("Status"),
    )
    is_bot = models.BooleanField(default=False, verbose_name=_("Is Bot"))
    is_premium = models.BooleanField(default=False, verbose_name=_("Has Telegram Premium"))

    # Activity tracking
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Activity"))
    total_transcriptions = models.IntegerField(default=0, verbose_name=_("Total Transcriptions"))
    total_spent = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("Total Spent")
    )

    # Notifications
    notifications_enabled = models.BooleanField(
        default=True, verbose_name=_("Notifications Enabled")
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "telegram_users"
        verbose_name = _("Telegram User")
        verbose_name_plural = _("Telegram Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["telegram_id"]),
            models.Index(fields=["telegram_username"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"@{self.telegram_username or self.telegram_id}"

    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]

    @property
    def is_active_user(self):
        """Check if user is active"""
        return self.status == UserStatus.ACTIVE.value

    async def get_wallet(self, session=None):
        """Get user's wallet"""
        from apps.wallet.models import Wallet

        return await Wallet.objects.aget(user=self)

    def block(self):
        """Block user"""
        self.status = UserStatus.BLOCKED.value
        self.save(update_fields=["status"])

    def unblock(self):
        """Unblock user"""
        self.status = UserStatus.ACTIVE.value
        self.save(update_fields=["status"])
