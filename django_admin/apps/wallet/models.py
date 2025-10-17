from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from core.exceptions import InsufficientBalanceError


class Wallet(models.Model):
    """User wallet model"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name=_("User")
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1000.00'),
        verbose_name=_("Balance")
    )
    currency = models.CharField(
        max_length=3,
        default='UZS',
        verbose_name=_("Currency")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    # Limits
    daily_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Daily Spending Limit")
    )
    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Monthly Spending Limit")
    )

    # Statistics
    total_credited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Total Credited")
    )
    total_debited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Total Debited")
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    last_transaction_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Transaction At")
    )

    class Meta:
        db_table = 'wallets'
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Wallet of {self.user} - {self.balance} {self.currency}"

    def add_balance(self, amount: Decimal, description: str = None):
        """Add amount to wallet balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.balance += amount
        self.total_credited += amount
        self.save(update_fields=['balance', 'total_credited', 'updated_at'])

        # Create transaction record
        from apps.transactions.models import Transaction
        Transaction.objects.create(
            user=self.user,
            wallet=self,
            type='credit',
            amount=amount,
            balance_after=self.balance,
            description=description or "Balance added",
            status='completed'
        )

        return self.balance

    def deduct_balance(self, amount: Decimal, description: str = None):
        """Deduct amount from wallet balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if self.balance < amount:
            raise InsufficientBalanceError(
                required=float(amount),
                available=float(self.balance)
            )

        self.balance -= amount
        self.total_debited += amount
        self.save(update_fields=['balance', 'total_debited', 'updated_at'])

        # Create transaction record
        from apps.transactions.models import Transaction
        Transaction.objects.create(
            user=self.user,
            wallet=self,
            type='debit',
            amount=amount,
            balance_after=self.balance,
            description=description or "Balance deducted",
            status='completed'
        )

        return self.balance

    def check_balance(self, amount: Decimal) -> bool:
        """Check if wallet has sufficient balance"""
        return self.balance >= amount

    def get_daily_spent(self):
        """Get amount spent today"""
        from django.utils import timezone
        from django.db.models import Sum
        from apps.transactions.models import Transaction

        today = timezone.now().date()
        spent = Transaction.objects.filter(
            wallet=self,
            type='debit',
            status='completed',
            created_at__date=today
        ).aggregate(Sum('amount'))['amount__sum']

        return spent or Decimal('0.00')

    def get_monthly_spent(self):
        """Get amount spent this month"""
        from django.utils import timezone
        from django.db.models import Sum
        from apps.transactions.models import Transaction

        now = timezone.now()
        spent = Transaction.objects.filter(
            wallet=self,
            type='debit',
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(Sum('amount'))['amount__sum']

        return spent or Decimal('0.00')