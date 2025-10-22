import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.enums import PaymentMethod, TransactionStatus, TransactionType


class Transaction(models.Model):
    """Transaction model"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("User"),
    )
    wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Wallet"),
    )

    # Transaction details
    type = models.CharField(
        max_length=20, choices=[(t.value, t.name) for t in TransactionType], verbose_name=_("Type")
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Amount"))
    balance_before = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_("Balance Before")
    )
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_("Balance After")
    )

    # Payment details
    payment_method = models.CharField(
        max_length=20,
        choices=[(m.value, m.name) for m in PaymentMethod],
        null=True,
        blank=True,
        verbose_name=_("Payment Method"),
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in TransactionStatus],
        default=TransactionStatus.PENDING.value,
        verbose_name=_("Status"),
    )

    # References
    reference_id = models.CharField(
        max_length=255, unique=True, default=uuid.uuid4, verbose_name=_("Reference ID")
    )
    external_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("External Transaction ID")
    )

    # Related object (e.g., transcription)
    related_object_type = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Related Object Type")
    )
    related_object_id = models.IntegerField(
        null=True, blank=True, verbose_name=_("Related Object ID")
    )

    # Additional info
    description = models.TextField(blank=True, verbose_name=_("Description"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))

    # Payment gateway info (for bot compatibility)
    gateway = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Payment Gateway")
    )
    gateway_transaction_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("Gateway Transaction ID")
    )

    # Processing info
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Processed At"))
    failed_reason = models.TextField(blank=True, verbose_name=_("Failed Reason"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "transactions"
        db_table = "transactions"
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reference_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} - {self.user}"

    def complete(self):
        """Mark transaction as completed"""
        from django.utils import timezone

        self.status = TransactionStatus.COMPLETED.value
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "processed_at", "updated_at"])

    def fail(self, reason: str):
        """Mark transaction as failed"""
        from django.utils import timezone

        self.status = TransactionStatus.FAILED.value
        self.failed_reason = reason
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "failed_reason", "processed_at", "updated_at"])

    def cancel(self):
        """Cancel transaction"""
        self.status = TransactionStatus.CANCELLED.value
        self.save(update_fields=["status", "updated_at"])

    @property
    def is_completed(self):
        return self.status == TransactionStatus.COMPLETED.value

    @property
    def is_credit(self):
        return self.type in [TransactionType.CREDIT.value, TransactionType.BONUS.value]

    @property
    def is_debit(self):
        return self.type == TransactionType.DEBIT.value
