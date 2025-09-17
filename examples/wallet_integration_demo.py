#!/usr/bin/env python3
"""
Wallet and Transaction Integration Demo

This script demonstrates how to use the integrated wallet and transaction system
in the TranscriptionBot project. It shows various wallet operations and how
transactions are automatically logged.

Usage:
    python examples/wallet_integration_demo.py
"""

import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_admin.config.settings.local')
django.setup()

from django_admin.apps.users.models import User
from services.payment.wallet_service import WalletService
from core.enums import TransactionType, PaymentMethod


def create_demo_user():
    """Create a demo user for testing."""
    user, created = User.objects.get_or_create(
        telegram_id=123456789,
        defaults={
            'username': 'demo_user',
            'first_name': 'Demo',
            'last_name': 'User',
            'role': 'user'
        }
    )

    if created:
        print(f"✅ Created demo user: {user.first_name} {user.last_name} (ID: {user.telegram_id})")
    else:
        print(f"📋 Using existing demo user: {user.first_name} {user.last_name} (ID: {user.telegram_id})")

    return user


def demonstrate_wallet_operations():
    """Demonstrate various wallet operations."""
    print("\n" + "="*60)
    print("🚀 WALLET & TRANSACTION INTEGRATION DEMO")
    print("="*60)

    # Create demo user
    user = create_demo_user()

    # 1. Get or create wallet
    print(f"\n1️⃣ Getting wallet for user {user.telegram_id}...")
    wallet = WalletService.get_or_create_wallet(user)
    print(f"   💰 Initial balance: {wallet.balance} {wallet.currency}")

    # 2. Get balance info
    print(f"\n2️⃣ Getting detailed balance information...")
    balance_info = WalletService.get_balance_info(user)
    print(f"   💵 Current Balance: {balance_info.current_balance}")
    print(f"   📈 Total Credited: {balance_info.total_credited}")
    print(f"   📉 Total Debited: {balance_info.total_debited}")
    print(f"   📊 Daily Spent: {balance_info.daily_spent}")
    print(f"   📊 Monthly Spent: {balance_info.monthly_spent}")
    print(f"   ✅ Wallet Active: {balance_info.is_active}")

    # 3. Add balance (simulating payment)
    print(f"\n3️⃣ Adding balance via PayMe payment...")
    add_result = WalletService.add_balance(
        user=user,
        amount=Decimal('5000.00'),
        description="PayMe deposit - Demo transaction",
        payment_method=PaymentMethod.PAYME,
        external_id="PAYME_123456",
        metadata={"payment_gateway": "payme", "test_mode": True}
    )

    if add_result.success:
        print(f"   ✅ Successfully added balance!")
        print(f"   🆔 Transaction ID: {add_result.transaction_id}")
        print(f"   💰 New Balance: {add_result.balance_after}")
    else:
        print(f"   ❌ Failed to add balance: {add_result.error}")

    # 4. Calculate transcription cost
    print(f"\n4️⃣ Calculating transcription cost...")
    duration_seconds = 180  # 3 minutes
    media_type = "audio"
    cost = WalletService.calculate_transcription_cost(
        duration_seconds=duration_seconds,
        media_type=media_type,
        quality_level="normal"
    )
    print(f"   🎵 Media Type: {media_type}")
    print(f"   ⏱️ Duration: {duration_seconds} seconds ({duration_seconds//60} minutes)")
    print(f"   💸 Calculated Cost: {cost}")

    # 5. Check sufficient balance
    print(f"\n5️⃣ Checking balance sufficiency...")
    has_balance = WalletService.check_sufficient_balance(user, cost)
    print(f"   💰 Required: {cost}")
    print(f"   ✅ Sufficient Balance: {has_balance}")

    # 6. Deduct balance (simulating transcription payment)
    print(f"\n6️⃣ Deducting balance for transcription...")
    deduct_result = WalletService.deduct_balance(
        user=user,
        amount=cost,
        description=f"Transcription service - {media_type} ({duration_seconds}s)",
        related_object_type="transcription",
        related_object_id=1,
        metadata={
            "media_type": media_type,
            "duration_seconds": duration_seconds,
            "quality_level": "normal"
        }
    )

    if deduct_result.success:
        print(f"   ✅ Successfully deducted balance!")
        print(f"   🆔 Transaction ID: {deduct_result.transaction_id}")
        print(f"   💰 Remaining Balance: {deduct_result.balance_after}")
    else:
        print(f"   ❌ Failed to deduct balance: {deduct_result.error}")

    # 7. Add bonus balance
    print(f"\n7️⃣ Adding bonus balance...")
    bonus_result = WalletService.add_balance(
        user=user,
        amount=Decimal('500.00'),
        description="Welcome bonus for new users",
        payment_method=PaymentMethod.BONUS,
        metadata={"bonus_type": "welcome", "promotion_id": "WELCOME2024"}
    )

    if bonus_result.success:
        print(f"   ✅ Bonus added successfully!")
        print(f"   💰 Bonus Amount: 500.00")
        print(f"   💰 New Balance: {bonus_result.balance_after}")

    # 8. Simulate refund
    print(f"\n8️⃣ Processing refund...")
    refund_result = WalletService.refund_balance(
        user=user,
        amount=cost / 2,  # Partial refund
        description="Partial refund for failed transcription",
        original_transaction_id=deduct_result.transaction_id,
        metadata={"refund_type": "partial", "refund_reason": "processing_failed"}
    )

    if refund_result.success:
        print(f"   ✅ Refund processed successfully!")
        print(f"   💰 Refund Amount: {cost / 2}")
        print(f"   💰 New Balance: {refund_result.balance_after}")

    # 9. Set wallet limits
    print(f"\n9️⃣ Setting wallet spending limits...")
    limits_set = WalletService.set_wallet_limits(
        user=user,
        daily_limit=Decimal('1000.00'),
        monthly_limit=Decimal('10000.00')
    )

    if limits_set:
        print(f"   ✅ Spending limits set successfully!")
        print(f"   📅 Daily Limit: 1,000.00 UZS")
        print(f"   📅 Monthly Limit: 10,000.00 UZS")

    # 10. Get transaction history
    print(f"\n🔟 Getting transaction history...")
    transactions = WalletService.get_transaction_history(
        user=user,
        limit=10
    )

    print(f"   📝 Found {len(transactions)} recent transactions:")
    for i, txn in enumerate(transactions, 1):
        type_emoji = "💰" if txn.is_credit else "💸"
        print(f"   {i}. {type_emoji} {txn.get_type_display()}: {txn.amount} - {txn.description}")

    # 11. Get spending summary
    print(f"\n1️⃣1️⃣ Getting spending summary...")
    summary = WalletService.get_spending_summary(user, days=30)
    print(f"   📊 Last 30 days spending:")
    print(f"   💸 Total Spent: {summary['total_spent']}")
    print(f"   📊 Transaction Count: {summary['transaction_count']}")
    print(f"   📈 Daily Average: {summary['daily_average']}")
    print(f"   💰 Current Balance: {summary['current_balance']}")

    # 12. Final balance check
    print(f"\n1️⃣2️⃣ Final balance summary...")
    final_balance = WalletService.get_balance_info(user)
    print(f"   💰 Final Balance: {final_balance.current_balance}")
    print(f"   📈 Total Credited: {final_balance.total_credited}")
    print(f"   📉 Total Debited: {final_balance.total_debited}")

    print(f"\n" + "="*60)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("="*60)

    return user


def demonstrate_error_handling():
    """Demonstrate error handling scenarios."""
    print(f"\n" + "="*60)
    print("⚠️  ERROR HANDLING DEMO")
    print("="*60)

    user = User.objects.get(telegram_id=123456789)

    # 1. Try to deduct more than available balance
    print(f"\n1️⃣ Testing insufficient balance scenario...")
    current_balance = WalletService.get_balance_info(user).current_balance
    excessive_amount = current_balance + Decimal('1000.00')

    result = WalletService.deduct_balance(
        user=user,
        amount=excessive_amount,
        description="Test insufficient balance"
    )

    if not result.success:
        print(f"   ✅ Correctly handled insufficient balance!")
        print(f"   ❌ Error: {result.error}")

    # 2. Try invalid amount
    print(f"\n2️⃣ Testing invalid amount scenario...")
    result = WalletService.add_balance(
        user=user,
        amount=Decimal('-100.00'),
        description="Test negative amount"
    )

    if not result.success:
        print(f"   ✅ Correctly handled negative amount!")
        print(f"   ❌ Error: {result.error}")

    print(f"\n" + "="*60)
    print("✅ ERROR HANDLING DEMO COMPLETED!")
    print("="*60)


def demonstrate_advanced_features():
    """Demonstrate advanced wallet features."""
    print(f"\n" + "="*60)
    print("🚀 ADVANCED FEATURES DEMO")
    print("="*60)

    user = User.objects.get(telegram_id=123456789)

    # 1. Test daily spending limit
    print(f"\n1️⃣ Testing daily spending limit...")

    # Try to spend more than daily limit
    daily_limit = Decimal('1000.00')
    large_amount = Decimal('1200.00')

    result = WalletService.deduct_balance(
        user=user,
        amount=large_amount,
        description="Test daily limit"
    )

    if not result.success and "daily limit" in result.error.lower():
        print(f"   ✅ Daily limit protection working!")
        print(f"   ❌ Error: {result.error}")

    # 2. Demonstrate transaction filtering
    print(f"\n2️⃣ Testing transaction filtering...")

    credit_transactions = WalletService.get_transaction_history(
        user=user,
        transaction_type=TransactionType.CREDIT,
        limit=5
    )

    debit_transactions = WalletService.get_transaction_history(
        user=user,
        transaction_type=TransactionType.DEBIT,
        limit=5
    )

    print(f"   💰 Credit transactions: {len(credit_transactions)}")
    print(f"   💸 Debit transactions: {len(debit_transactions)}")

    # 3. Wallet deactivation/activation test
    print(f"\n3️⃣ Testing wallet activation controls...")

    # Deactivate wallet
    deactivated = WalletService.deactivate_wallet(user)
    if deactivated:
        print(f"   ✅ Wallet deactivated successfully")

        # Try to spend from deactivated wallet
        result = WalletService.deduct_balance(
            user=user,
            amount=Decimal('100.00'),
            description="Test deactivated wallet"
        )

        if not result.success:
            print(f"   ✅ Correctly blocked transaction from inactive wallet!")
            print(f"   ❌ Error: {result.error}")

    # Reactivate wallet
    reactivated = WalletService.activate_wallet(user)
    if reactivated:
        print(f"   ✅ Wallet reactivated successfully")

    print(f"\n" + "="*60)
    print("✅ ADVANCED FEATURES DEMO COMPLETED!")
    print("="*60)


def main():
    """Main demo function."""
    print("🎯 Starting Wallet & Transaction Integration Demo...")

    try:
        # Run basic operations demo
        user = demonstrate_wallet_operations()

        # Run error handling demo
        demonstrate_error_handling()

        # Run advanced features demo
        demonstrate_advanced_features()

        print(f"\n🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print(f"📊 Check your database to see all the transactions that were logged automatically!")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()