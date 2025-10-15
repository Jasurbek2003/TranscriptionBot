"""Django ORM-based wallet service for handling wallet operations."""

import logging
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
from asgiref.sync import sync_to_async
from django.db.models import Sum, Q
from django.utils import timezone

# Import Django models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'django_admin'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.users.models import TelegramUser
from apps.wallet.models import Wallet
from apps.transactions.models import Transaction
from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TransactionResult:
    """Transaction operation result."""
    success: bool
    transaction_id: Optional[str] = None
    balance_after: Optional[Decimal] = None
    error: Optional[str] = None


@dataclass
class BalanceInfo:
    """Wallet balance information."""
    current_balance: Decimal
    total_credited: Decimal
    total_debited: Decimal
    is_active: bool


class WalletService:
    """Service for wallet operations and transaction management using Django ORM."""

    @sync_to_async
    def get_or_create_wallet(self, user: TelegramUser) -> Wallet:
        """Get or create wallet for user."""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={
                'balance': settings.pricing.initial_balance,
                'currency': 'UZS'
            }
        )
        if created:
            logger.info(f"Created new wallet for user {user.id}")
        return wallet

    @sync_to_async
    def get_balance_info(self, user: TelegramUser) -> BalanceInfo:
        """Get comprehensive balance information."""
        wallet = Wallet.objects.get(user=user)

        # Calculate totals from transactions
        transactions = Transaction.objects.filter(
            user=user,
            status='completed'
        )

        total_credited = transactions.filter(type='credit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_debited = transactions.filter(type='debit').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        return BalanceInfo(
            current_balance=wallet.balance,
            total_credited=total_credited,
            total_debited=total_debited,
            is_active=True
        )

    @sync_to_async
    def add_balance(
        self,
        user: TelegramUser,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None,
        gateway: Optional[str] = None,
        gateway_transaction_id: Optional[str] = None
    ) -> TransactionResult:
        """Add balance to user's wallet."""
        try:
            if amount <= 0:
                return TransactionResult(
                    success=False,
                    error="Amount must be positive"
                )

            wallet = Wallet.objects.get(user=user)
            balance_before = wallet.balance

            # Update wallet balance
            wallet.balance += amount
            wallet.total_credited += amount
            wallet.last_transaction_at = timezone.now()
            wallet.save()

            # Create transaction record
            transaction = Transaction.objects.create(
                user=user,
                wallet=wallet,
                type='credit',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status='completed',
                reference_id=reference_id,
                gateway=gateway,
                gateway_transaction_id=gateway_transaction_id
            )

            logger.info(f"Added {amount} to wallet of user {user.id}. New balance: {wallet.balance}")

            return TransactionResult(
                success=True,
                transaction_id=str(transaction.id),
                balance_after=wallet.balance
            )

        except Exception as e:
            logger.error(f"Error adding balance for user {user.id}: {e}")
            return TransactionResult(
                success=False,
                error=str(e)
            )

    @sync_to_async
    def deduct_balance(
        self,
        user: TelegramUser,
        amount: Decimal,
        description: str,
        reference_id: Optional[str] = None,
        skip_balance_check: bool = False
    ) -> TransactionResult:
        """Deduct balance from user's wallet."""
        try:
            if amount <= 0:
                return TransactionResult(
                    success=False,
                    error="Amount must be positive"
                )

            # Check for existing transaction with same reference_id
            if reference_id:
                existing = Transaction.objects.filter(
                    reference_id=reference_id,
                    user=user,
                    status='completed'
                ).first()

                if existing:
                    logger.warning(f"Transaction with reference_id {reference_id} already exists for user {user.id}")
                    return TransactionResult(
                        success=False,
                        error=f"Transaction already processed (reference: {reference_id})"
                    )

            wallet = Wallet.objects.get(user=user)
            balance_before = wallet.balance

            # Check sufficient balance
            if not skip_balance_check and wallet.balance < amount:
                return TransactionResult(
                    success=False,
                    error=f"Insufficient balance. Required: {amount}, Available: {wallet.balance}"
                )

            # Update wallet balance
            wallet.balance -= amount
            wallet.total_debited += amount
            wallet.last_transaction_at = timezone.now()
            wallet.save()

            # Create transaction record
            transaction = Transaction.objects.create(
                user=user,
                wallet=wallet,
                type='debit',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status='completed',
                reference_id=reference_id
            )

            logger.info(f"Deducted {amount} from wallet of user {user.id}. New balance: {wallet.balance}")

            return TransactionResult(
                success=True,
                transaction_id=str(transaction.id),
                balance_after=wallet.balance
            )

        except Exception as e:
            logger.error(f"Error deducting balance for user {user.id}: {e}")
            return TransactionResult(
                success=False,
                error=str(e)
            )

    @sync_to_async
    def get_transaction_history(
        self,
        user: TelegramUser,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """Get user's transaction history."""
        transactions = Transaction.objects.filter(
            user=user
        ).order_by('-created_at')[offset:offset + limit]
        return list(transactions)

    @sync_to_async
    def check_sufficient_balance(self, user: TelegramUser, amount: Decimal) -> bool:
        """Check if user has sufficient balance."""
        wallet = Wallet.objects.get(user=user)
        return wallet.balance >= amount

    async def calculate_transcription_cost(
        self,
        duration_seconds: int,
        media_type: str
    ) -> Decimal:
        """Calculate transcription cost based on duration and type."""
        duration_minutes = max(1, (duration_seconds + 59) // 60)  # Round up

        if media_type.lower() in ['video', 'video_note']:
            base_cost = settings.pricing.video_price_per_min
        else:
            base_cost = settings.pricing.audio_price_per_min

        total_cost = Decimal(str(base_cost * duration_minutes))
        return total_cost.quantize(Decimal('0.01'))
