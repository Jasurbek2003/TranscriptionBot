"""
Tests for Payme payment gateway webhook handlers.

Tests cover:
- CheckPerformTransaction
- CreateTransaction
- PerformTransaction
- CancelTransaction
- CheckTransaction
- GetStatement
- JSON-RPC 2.0 protocol
- Authentication
- Error handling
"""

import base64
import json
from datetime import datetime, timedelta
from decimal import Decimal

from apps.transactions.models import Transaction
from apps.users.models import TelegramUser
from apps.wallet.models import Wallet
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone


class PaymeWebhookTest(TestCase):
    """Test suite for Payme payment webhook"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()

        # Create test user
        self.user = TelegramUser.objects.create(
            telegram_id=987654321, username="paymeuser", first_name="Payme", last_name="Test"
        )

        # Create wallet for user
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal("0.00"))

        # Create test transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            wallet=self.wallet,
            type="credit",
            status="pending",
            amount=Decimal("50000.00"),
            payment_method="payme",
            description="Payme test payment",
        )

        # Payme merchant credentials for testing
        self.merchant_id = "test_merchant_id"
        self.secret_key = "test_secret_key"

    def get_auth_header(self):
        """Generate Basic Auth header for Payme"""
        credentials = f"Paycom:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def payme_request(self, method, params=None, request_id=1):
        """Make a Payme JSON-RPC request"""
        payload = {"method": method, "params": params or {}, "id": request_id}

        with self.settings(
                PAYME_MERCHANT_ID=self.merchant_id, PAYME_SECRET_KEY=self.secret_key, DEBUG=True
        ):
            response = self.client.post(
                reverse("transactions:payme_webhook"),
                data=json.dumps(payload),
                content_type="application/json",
                headers={"authorization": self.get_auth_header()},
            )

        return response

    def test_check_perform_transaction_success(self):
        """Test CheckPerformTransaction with valid transaction"""
        params = {
            "amount": 5000000,  # 50000.00 UZS in tiyin
            "account": {"order_id": str(self.transaction.reference_id)},
        }

        response = self.payme_request("CheckPerformTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["allow"], True)

    def test_check_perform_transaction_invalid_order(self):
        """Test CheckPerformTransaction with invalid order_id"""
        params = {"amount": 5000000, "account": {"order_id": "invalid-uuid"}}

        response = self.payme_request("CheckPerformTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -31050)  # INVALID_ACCOUNT

    def test_check_perform_transaction_amount_mismatch(self):
        """Test CheckPerformTransaction with wrong amount"""
        params = {
            "amount": 1000000,  # Wrong amount
            "account": {"order_id": str(self.transaction.reference_id)},
        }

        response = self.payme_request("CheckPerformTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -31001)  # INVALID_AMOUNT

    def test_create_transaction_success(self):
        """Test CreateTransaction"""
        payme_trans_id = "payme_trans_123456"
        params = {
            "id": payme_trans_id,
            "time": int(datetime.now().timestamp() * 1000),
            "amount": 5000000,
            "account": {"order_id": str(self.transaction.reference_id)},
        }

        response = self.payme_request("CreateTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], 1)  # CREATED

        # Verify transaction was updated
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.external_id, payme_trans_id)
        self.assertEqual(self.transaction.gateway, "payme")

    def test_create_transaction_idempotency(self):
        """Test CreateTransaction idempotency"""
        payme_trans_id = "payme_trans_123456"
        self.transaction.external_id = payme_trans_id
        self.transaction.gateway = "payme"
        self.transaction.save()

        params = {
            "id": payme_trans_id,
            "time": int(datetime.now().timestamp() * 1000),
            "amount": 5000000,
            "account": {"order_id": str(self.transaction.reference_id)},
        }

        response = self.payme_request("CreateTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], 1)

    def test_perform_transaction_success(self):
        """Test PerformTransaction"""
        payme_trans_id = "payme_trans_789"
        self.transaction.external_id = payme_trans_id
        self.transaction.gateway = "payme"
        self.transaction.save()

        initial_balance = self.wallet.balance

        params = {"id": payme_trans_id}

        response = self.payme_request("PerformTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], 2)  # COMPLETED

        # Verify transaction completed
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "completed")

        # Verify wallet balance
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, initial_balance + self.transaction.amount)

    def test_perform_transaction_not_found(self):
        """Test PerformTransaction with non-existent transaction"""
        params = {"id": "nonexistent_trans_id"}

        response = self.payme_request("PerformTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -31003)  # TRANSACTION_NOT_FOUND

    def test_cancel_transaction_before_perform(self):
        """Test CancelTransaction before PerformTransaction"""
        payme_trans_id = "payme_trans_cancel_1"
        self.transaction.external_id = payme_trans_id
        self.transaction.gateway = "payme"
        self.transaction.status = "pending"
        self.transaction.save()

        params = {"id": payme_trans_id, "reason": 5}  # Cancelled by timeout

        response = self.payme_request("CancelTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], -1)  # CANCELLED

        # Verify transaction status
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "cancelled")

    def test_cancel_transaction_after_perform(self):
        """Test CancelTransaction after PerformTransaction (refund)"""
        payme_trans_id = "payme_trans_cancel_2"
        self.transaction.external_id = payme_trans_id
        self.transaction.gateway = "payme"
        self.transaction.status = "completed"
        self.transaction.save()

        # Add balance to wallet
        self.wallet.balance = Decimal("50000.00")
        self.wallet.save()

        params = {"id": payme_trans_id, "reason": 5}

        response = self.payme_request("CancelTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], -2)  # CANCELLED_AFTER_COMPLETE

        # Verify transaction refunded
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, "refunded")

        # Verify wallet balance deducted
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_check_transaction(self):
        """Test CheckTransaction"""
        payme_trans_id = "payme_trans_check"
        self.transaction.external_id = payme_trans_id
        self.transaction.gateway = "payme"
        self.transaction.status = "completed"
        self.transaction.processed_at = timezone.now()
        self.transaction.save()

        params = {"id": payme_trans_id}

        response = self.payme_request("CheckTransaction", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["result"]["state"], 2)  # COMPLETED
        self.assertIn("create_time", data["result"])
        self.assertIn("perform_time", data["result"])

    def test_get_statement(self):
        """Test GetStatement"""
        # Create multiple transactions
        for i in range(3):
            trans = Transaction.objects.create(
                user=self.user,
                wallet=self.wallet,
                type="credit",
                status="completed",
                amount=Decimal("10000.00"),
                payment_method="payme",
                gateway="payme",
                external_id=f"payme_trans_{i}",
                description=f"Test transaction {i}",
            )

        now = datetime.now()
        from_time = int((now - timedelta(days=1)).timestamp() * 1000)
        to_time = int((now + timedelta(days=1)).timestamp() * 1000)

        params = {"from": from_time, "to": to_time}

        response = self.payme_request("GetStatement", params)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertIn("transactions", data["result"])
        self.assertGreaterEqual(len(data["result"]["transactions"]), 3)

    def test_unauthorized_request(self):
        """Test request without authorization"""
        payload = {"method": "CheckPerformTransaction", "params": {}, "id": 1}

        response = self.client.post(
            reverse("transactions:payme_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -32504)  # INSUFFICIENT_PRIVILEGES

    def test_invalid_json(self):
        """Test request with invalid JSON"""
        with self.settings(
                PAYME_MERCHANT_ID=self.merchant_id, PAYME_SECRET_KEY=self.secret_key, DEBUG=True
        ):
            response = self.client.post(
                reverse("transactions:payme_webhook"),
                data="invalid json{",
                content_type="application/json",
                headers={"authorization": self.get_auth_header()},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -32700)  # PARSE_ERROR

    def test_unknown_method(self):
        """Test request with unknown method"""
        response = self.payme_request("UnknownMethod", {})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -32601)  # METHOD_NOT_FOUND
