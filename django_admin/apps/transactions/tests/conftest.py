"""
Pytest configuration and fixtures for transaction tests.
"""

from decimal import Decimal

import pytest
from apps.transactions.models import Transaction
from apps.users.models import TelegramUser
from apps.wallet.models import Wallet


@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = TelegramUser.objects.create(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
    )
    return user


@pytest.fixture
def test_wallet(test_user):
    """Create a test wallet"""
    wallet = Wallet.objects.create(user=test_user, balance=Decimal("1000.00"), currency="UZS")
    return wallet


@pytest.fixture
def test_transaction(test_user, test_wallet):
    """Create a test transaction"""
    transaction = Transaction.objects.create(
        user=test_user,
        wallet=test_wallet,
        type="credit",
        status="pending",
        amount=Decimal("10000.00"),
        payment_method="payme",
        description="Test transaction",
    )
    return transaction


@pytest.fixture
def api_client():
    """Create an API client"""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture(autouse=True)
def setup_test_settings(settings):
    """Configure test settings"""
    settings.DEBUG = True
    settings.PAYME_MERCHANT_ID = "test_merchant"
    settings.PAYME_SECRET_KEY = "test_secret"
    settings.CLICK_MERCHANT_ID = "test_click_merchant"
    settings.CLICK_SERVICE_ID = "test_click_service"
    settings.CLICK_SECRET_KEY = "test_click_secret"
