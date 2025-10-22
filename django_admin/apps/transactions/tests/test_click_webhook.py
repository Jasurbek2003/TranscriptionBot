"""
Tests for Click payment gateway webhook handlers.

Tests cover:
- Prepare request (action=0)
- Complete request (action=1)
- Signature verification
- Error handling
- Transaction status updates
"""

import hashlib
from decimal import Decimal
from unittest.mock import patch

from apps.transactions.models import Transaction
from apps.users.models import TelegramUser
from apps.wallet.models import Wallet
from django.test import Client, TestCase
from django.urls import reverse


class ClickWebhookTest(TestCase):
    """Test suite for Click payment webhook"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()

        # Create test user
        self.user = TelegramUser.objects.create(
            telegram_id=12345678, username="testuser", first_name="Test", last_name="User"
        )

        # Create wallet for user
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal("0.00"))

        # Create test transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            wallet=self.wallet,
            type="credit",
            status="pending",
            amount=Decimal("10000.00"),
            payment_method="click",
            description="Test payment",
        )

    def generate_click_signature(self, params, action="0", merchant_prepare_id=None):
        """Generate Click signature for testing"""
        secret_key = "test_secret_key"

        if action == "1" and merchant_prepare_id:
            # Complete signature includes merchant_prepare_id
            sign_string = f"{params['click_trans_id']}{params['service_id']}{secret_key}{params['merchant_trans_id']}{merchant_prepare_id}{params['amount']}{params['action']}{params['sign_time']}"
        else:
            # Prepare signature
            sign_string = f"{params['click_trans_id']}{params['service_id']}{secret_key}{params['merchant_trans_id']}{params['amount']}{params['action']}{params['sign_time']}"

        return hashlib.md5(sign_string.encode()).hexdigest()

    @patch("apps.transactions.views.django_settings")
    def test_click_prepare_success(self, mock_settings):
        """Test successful Click prepare request"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": str(self.transaction.reference_id),
            "amount": "10000.00",
            "action": "0",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
        }
        params["sign"] = self.generate_click_signature(params, action="0")

        response = self.client.post(reverse("transactions:click_prepare"), data=params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], 0)
        self.assertEqual(data["error_note"], "Success")

        # Verify transaction was updated
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.gateway, "click")
        self.assertEqual(self.transaction.gateway_transaction_id, "123456")

    @patch("apps.transactions.views.django_settings")
    def test_click_complete_success(self, mock_settings):
        """Test successful Click complete request"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        # Set transaction as prepared
        self.transaction.gateway = "click"
        self.transaction.gateway_transaction_id = "123456"
        self.transaction.save()

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": str(self.transaction.reference_id),
            "merchant_prepare_id": str(self.transaction.id),
            "amount": "10000.00",
            "action": "1",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
        }
        params["sign"] = self.generate_click_signature(
            params, action="1", merchant_prepare_id=str(self.transaction.id)
        )

        initial_balance = self.wallet.balance

        response = self.client.post(reverse("transactions:click_complete"), data=params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], 0)

        # Verify transaction status
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "completed")

        # Verify wallet balance updated
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance + self.transaction.amount)

    @patch("apps.transactions.views.django_settings")
    def test_click_prepare_invalid_signature(self, mock_settings):
        """Test Click prepare with invalid signature"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": str(self.transaction.reference_id),
            "amount": "10000.00",
            "action": "0",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
            "sign": "invalid_signature",
        }

        response = self.client.post(reverse("transactions:click_prepare"), data=params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], -1)  # SIGN_CHECK_FAILED

    @patch("apps.transactions.views.django_settings")
    def test_click_prepare_transaction_not_found(self, mock_settings):
        """Test Click prepare with non-existent transaction"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": "nonexistent-uuid",
            "amount": "10000.00",
            "action": "0",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
        }
        params["sign"] = self.generate_click_signature(params, action="0")

        response = self.client.post(reverse("transactions:click_prepare"), data=params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], -5)  # TRANSACTION_DOES_NOT_EXIST

    @patch("apps.transactions.views.django_settings")
    def test_click_prepare_amount_mismatch(self, mock_settings):
        """Test Click prepare with amount mismatch"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": str(self.transaction.reference_id),
            "amount": "5000.00",  # Different from transaction amount
            "action": "0",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
        }
        params["sign"] = self.generate_click_signature(params, action="0")

        response = self.client.post(reverse("transactions:click_prepare"), data=params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], -2)  # INVALID_AMOUNT

    @patch("apps.transactions.views.django_settings")
    def test_click_complete_idempotency(self, mock_settings):
        """Test Click complete idempotency (calling twice)"""
        mock_settings.CLICK_MERCHANT_ID = "test_merchant"
        mock_settings.CLICK_SERVICE_ID = "test_service"
        mock_settings.CLICK_SECRET_KEY = "test_secret_key"
        mock_settings.DEBUG = True

        # Mark transaction as completed
        self.transaction.status = "completed"
        self.transaction.gateway = "click"
        self.transaction.gateway_transaction_id = "123456"
        self.transaction.save()

        params = {
            "click_trans_id": "123456",
            "service_id": "test_service",
            "click_paydoc_id": "654321",
            "merchant_trans_id": str(self.transaction.reference_id),
            "merchant_prepare_id": str(self.transaction.id),
            "amount": "10000.00",
            "action": "1",
            "error": "0",
            "error_note": "",
            "sign_time": "2024-01-01 00:00:00",
        }
        params["sign"] = self.generate_click_signature(
            params, action="1", merchant_prepare_id=str(self.transaction.id)
        )

        response = self.client.post(reverse("transactions:click_complete"), data=params)

        # Should return success (idempotent)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["error"], 0)
