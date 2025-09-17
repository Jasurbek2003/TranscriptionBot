"""Wallet service for handling wallet operations and transaction logging."""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, date, UTC
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, Q

from django_admin.apps.wallet.models import Wallet
from django_admin.apps.transactions.models import Transaction
from django_admin.apps.users.models import User
from core.enums import TransactionType, TransactionStatus, PaymentMethod
from core.exceptions import InsufficientBalanceError
from bot.config import pricing_settings

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
    daily_spent: Decimal
    monthly_spent: Decimal
    daily_limit: Optional[Decimal]
    monthly_limit: Optional[Decimal]
    is_active: bool


class WalletService:
    """Service for wallet operations and transaction management."""

    @staticmethod
    def get_or_create_wallet(user: User) -> Wallet:
        """Get or create wallet for user."""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={
                'balance': Decimal(str(pricing_settings.initial_balance)),
                'currency': 'UZS',
                'is_active': True
            }
        )

        if created:
            logger.info(f"Created new wallet for user {user.id}")
            # Create initial transaction record
            WalletService._create_transaction(
                user=user,
                wallet=wallet,
                transaction_type=TransactionType.BONUS,
                amount=wallet.balance,
                balance_before=Decimal('0.00'),
                balance_after=wallet.balance,
                description="Initial wallet balance",
                status=TransactionStatus.COMPLETED,
                payment_method=PaymentMethod.ADMIN
            )

        return wallet

    @staticmethod
    def get_balance_info(user: User) -> BalanceInfo:
        """Get comprehensive balance information."""
        wallet = WalletService.get_or_create_wallet(user)

        return BalanceInfo(
            current_balance=wallet.balance,
            total_credited=wallet.total_credited,
            total_debited=wallet.total_debited,
            daily_spent=wallet.get_daily_spent(),
            monthly_spent=wallet.get_monthly_spent(),
            daily_limit=wallet.daily_limit,
            monthly_limit=wallet.monthly_limit,
            is_active=wallet.is_active
        )

    @staticmethod
    @transaction.atomic
    def add_balance(
        user: User,
        amount: Decimal,
        description: str,
        payment_method: PaymentMethod = PaymentMethod.ADMIN,
        external_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionResult:
        """Add balance to user's wallet."""
        try:
            if amount <= 0:
                return TransactionResult(
                    success=False,
                    error="Amount must be positive"
                )

            wallet = WalletService.get_or_create_wallet(user)
            balance_before = wallet.balance

            # Update wallet balance
            wallet.balance += amount
            wallet.total_credited += amount
            wallet.last_transaction_at = timezone.now()
            wallet.save(update_fields=['balance', 'total_credited', 'last_transaction_at', 'updated_at'])

            # Create transaction record
            txn = WalletService._create_transaction(
                user=user,
                wallet=wallet,
                transaction_type=TransactionType.CREDIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status=TransactionStatus.COMPLETED,
                payment_method=payment_method,
                external_id=external_id,
                metadata=metadata or {}
            )

            logger.info(f"Added {amount} to wallet of user {user.id}. New balance: {wallet.balance}")

            return TransactionResult(
                success=True,
                transaction_id=txn.reference_id,
                balance_after=wallet.balance
            )

        except Exception as e:
            logger.error(f"Error adding balance for user {user.id}: {e}")
            return TransactionResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    @transaction.atomic
    def deduct_balance(
        user: User,
        amount: Decimal,
        description: str,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        skip_balance_check: bool = False
    ) -> TransactionResult:
        """Deduct balance from user's wallet."""
        try:
            if amount <= 0:
                return TransactionResult(
                    success=False,
                    error="Amount must be positive"
                )

            wallet = WalletService.get_or_create_wallet(user)

            if not wallet.is_active:
                return TransactionResult(
                    success=False,
                    error="Wallet is inactive"
                )

            balance_before = wallet.balance

            # Check sufficient balance
            if not skip_balance_check and wallet.balance < amount:
                return TransactionResult(
                    success=False,
                    error=f"Insufficient balance. Required: {amount}, Available: {wallet.balance}"
                )

            # Check daily limit
            if wallet.daily_limit:
                daily_spent = wallet.get_daily_spent()
                if daily_spent + amount > wallet.daily_limit:
                    return TransactionResult(
                        success=False,
                        error=f"Daily limit exceeded. Limit: {wallet.daily_limit}, Current spent: {daily_spent}"
                    )

            # Check monthly limit
            if wallet.monthly_limit:
                monthly_spent = wallet.get_monthly_spent()
                if monthly_spent + amount > wallet.monthly_limit:
                    return TransactionResult(
                        success=False,
                        error=f"Monthly limit exceeded. Limit: {wallet.monthly_limit}, Current spent: {monthly_spent}"
                    )

            # Update wallet balance
            wallet.balance -= amount
            wallet.total_debited += amount
            wallet.last_transaction_at = timezone.now()
            wallet.save(update_fields=['balance', 'total_debited', 'last_transaction_at', 'updated_at'])

            # Create transaction record
            txn = WalletService._create_transaction(
                user=user,
                wallet=wallet,
                transaction_type=TransactionType.DEBIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status=TransactionStatus.COMPLETED,
                payment_method=PaymentMethod.WALLET,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                metadata=metadata or {}
            )

            logger.info(f"Deducted {amount} from wallet of user {user.id}. New balance: {wallet.balance}")

            return TransactionResult(
                success=True,
                transaction_id=txn.reference_id,
                balance_after=wallet.balance
            )

        except Exception as e:
            logger.error(f"Error deducting balance for user {user.id}: {e}")
            return TransactionResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    @transaction.atomic
    def refund_balance(
        user: User,
        amount: Decimal,
        description: str,
        original_transaction_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionResult:
        """Refund balance to user's wallet."""
        try:
            if amount <= 0:
                return TransactionResult(
                    success=False,
                    error="Amount must be positive"
                )

            wallet = WalletService.get_or_create_wallet(user)
            balance_before = wallet.balance

            # Update wallet balance
            wallet.balance += amount
            wallet.total_credited += amount
            wallet.last_transaction_at = timezone.now()
            wallet.save(update_fields=['balance', 'total_credited', 'last_transaction_at', 'updated_at'])

            # Create refund transaction record
            refund_metadata = metadata or {}
            if original_transaction_id:
                refund_metadata['original_transaction_id'] = original_transaction_id

            txn = WalletService._create_transaction(
                user=user,
                wallet=wallet,
                transaction_type=TransactionType.REFUND,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                status=TransactionStatus.COMPLETED,
                payment_method=PaymentMethod.WALLET,
                metadata=refund_metadata
            )

            logger.info(f"Refunded {amount} to wallet of user {user.id}. New balance: {wallet.balance}")

            return TransactionResult(
                success=True,
                transaction_id=txn.reference_id,
                balance_after=wallet.balance
            )

        except Exception as e:
            logger.error(f"Error refunding balance for user {user.id}: {e}")
            return TransactionResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    def get_transaction_history(
        user: User,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Transaction]:
        """Get user's transaction history with filters."""
        queryset = Transaction.objects.filter(user=user)

        if transaction_type:
            queryset = queryset.filter(type=transaction_type.value)

        if status:
            queryset = queryset.filter(status=status.value)

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return list(queryset.order_by('-created_at')[offset:offset + limit])

    @staticmethod
    def get_spending_summary(user: User, days: int = 30) -> Dict[str, Any]:
        """Get spending summary for the last N days."""
        wallet = WalletService.get_or_create_wallet(user)
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)

        transactions = Transaction.objects.filter(
            user=user,
            type=TransactionType.DEBIT.value,
            status=TransactionStatus.COMPLETED.value,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_spent=Sum('amount'),
            transaction_count=Sum('id')
        )

        return {
            'total_spent': transactions['total_spent'] or Decimal('0.00'),
            'transaction_count': transactions['transaction_count'] or 0,
            'period_days': days,
            'start_date': start_date,
            'end_date': end_date,
            'current_balance': wallet.balance,
            'daily_average': (transactions['total_spent'] or Decimal('0.00')) / days
        }

    @staticmethod
    def check_sufficient_balance(user: User, amount: Decimal) -> bool:
        """Check if user has sufficient balance."""
        wallet = WalletService.get_or_create_wallet(user)
        return wallet.is_active and wallet.balance >= amount

    @staticmethod
    def set_wallet_limits(
        user: User,
        daily_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None
    ) -> bool:
        """Set wallet spending limits."""
        try:
            wallet = WalletService.get_or_create_wallet(user)

            if daily_limit is not None:
                wallet.daily_limit = daily_limit if daily_limit > 0 else None

            if monthly_limit is not None:
                wallet.monthly_limit = monthly_limit if monthly_limit > 0 else None

            wallet.save(update_fields=['daily_limit', 'monthly_limit', 'updated_at'])
            logger.info(f"Updated limits for user {user.id}: daily={daily_limit}, monthly={monthly_limit}")
            return True

        except Exception as e:
            logger.error(f"Error setting wallet limits for user {user.id}: {e}")
            return False

    @staticmethod
    def activate_wallet(user: User) -> bool:
        """Activate user's wallet."""
        try:
            wallet = WalletService.get_or_create_wallet(user)
            wallet.is_active = True
            wallet.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"Activated wallet for user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Error activating wallet for user {user.id}: {e}")
            return False

    @staticmethod
    def deactivate_wallet(user: User) -> bool:
        """Deactivate user's wallet."""
        try:
            wallet = WalletService.get_or_create_wallet(user)
            wallet.is_active = False
            wallet.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"Deactivated wallet for user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating wallet for user {user.id}: {e}")
            return False

    @staticmethod
    def _create_transaction(
        user: User,
        wallet: Wallet,
        transaction_type: TransactionType,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        description: str,
        status: TransactionStatus,
        payment_method: Optional[PaymentMethod] = None,
        external_id: Optional[str] = None,
        related_object_type: Optional[str] = None,
        related_object_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """Create a transaction record."""
        return Transaction.objects.create(
            user=user,
            wallet=wallet,
            type=transaction_type.value,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            payment_method=payment_method.value if payment_method else None,
            status=status.value,
            external_id=external_id,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            description=description,
            metadata=metadata or {},
            processed_at=timezone.now() if status == TransactionStatus.COMPLETED else None
        )

    @staticmethod
    def calculate_transcription_cost(
        duration_seconds: int,
        media_type: str,
        quality_level: str = "normal"
    ) -> Decimal:
        """Calculate transcription cost based on duration and type."""
        from core.enums import QualityLevel

        duration_minutes = max(1, duration_seconds // 60 + (1 if duration_seconds % 60 > 0 else 0))

        if media_type.lower() in ['video', 'video_note']:
            base_cost = pricing_settings.video_price_per_min
        else:
            base_cost = pricing_settings.audio_price_per_min

        quality_multiplier = QualityLevel.get_multiplier(quality_level)
        total_cost = Decimal(str(base_cost * duration_minutes * quality_multiplier))

        return total_cost.quantize(Decimal('0.01'))