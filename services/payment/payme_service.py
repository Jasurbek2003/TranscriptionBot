"""Payme payment gateway integration service.

Payme Uzbekistan payment system integration using JSON-RPC 2.0 protocol.
Official Documentation: https://developer.help.paycom.uz/
"""

import base64
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class PaymeService:
    """Payme payment gateway service implementing Merchant API specification.

    Payme uses JSON-RPC 2.0 protocol with the following methods:
    - CheckPerformTransaction: Check if transaction can be created
    - CreateTransaction: Create and reserve a transaction
    - PerformTransaction: Complete the transaction
    - CancelTransaction: Cancel/refund a transaction
    - CheckTransaction: Check transaction status
    - GetStatement: Get transactions for a period
    """

    # Payme error codes based on official documentation
    ERROR_CODES = {
        # General errors
        "INVALID_AMOUNT": -31001,
        "TRANSACTION_NOT_FOUND": -31003,
        "CANT_CANCEL_TRANSACTION": -31007,
        "CANT_PERFORM_OPERATION": -31008,
        # Account errors (customizable -31050 to -31099)
        "INVALID_ACCOUNT": -31050,
        "ALREADY_PROCESSED": -31051,
        # RPC errors
        "TRANSPORT_ERROR": -32300,
        "PARSE_ERROR": -32700,
        "INVALID_RPC_REQUEST": -32600,
        "METHOD_NOT_FOUND": -32601,
        "INSUFFICIENT_PRIVILEGES": -32504,
        "INTERNAL_ERROR": -32400,
    }

    # Transaction states
    STATES = {
        "CREATED": 1,  # Transaction created (reserved)
        "COMPLETED": 2,  # Transaction completed (performed)
        "CANCELLED": -1,  # Transaction cancelled before completion
        "CANCELLED_AFTER_COMPLETE": -2,  # Transaction cancelled after completion (refund)
    }

    # Cancellation reasons
    CANCEL_REASONS = {
        1: "Receivers not found",
        2: "Processing execution error",
        3: "Error in request from click",
        4: "Timeout (transaction expired - 12 hours)",
        5: "Refund",
        10: "Unknown",
    }

    def __init__(self, merchant_id: str, secret_key: str, test_mode: bool = True):
        """Initialize Payme service.

        Args:
            merchant_id: Payme merchant ID
            secret_key: Payme secret key for authentication
            test_mode: Whether to use test mode
        """
        self.merchant_id = merchant_id
        self.secret_key = secret_key
        self.test_mode = test_mode

        # Payme URLs
        self.checkout_url = (
            "https://checkout.paycom.uz" if not test_mode else "https://test.paycom.uz"
        )

    def create_payment_link(
            self, amount: float, order_id: str, return_url: Optional[str] = None
    ) -> str:
        """Create a payment link for user to complete payment.

        Args:
            amount: Payment amount in UZS (will be converted to tiyin - 1 UZS = 100 tiyin)
            order_id: Unique order/transaction ID
            return_url: URL to redirect after payment

        Returns:
            Payment URL string
        """
        try:
            # Convert to tiyin (1 UZS = 100 tiyin)
            amount_tiyin = int(amount * 100)

            # Build params
            params = {
                "m": self.merchant_id,
                "a": str(amount_tiyin),
                "ac.order_id": order_id,
            }

            if return_url:
                params["c"] = return_url

            payment_url = f"{self.checkout_url}?{urlencode(params)}"

            logger.info(
                f"Created Payme payment link for order {order_id}, "
                f"amount: {amount} UZS ({amount_tiyin} tiyin)"
            )
            return payment_url

        except Exception as e:
            logger.error(f"Error creating Payme payment link: {e}", exc_info=True)
            return ""

    def verify_auth(self, auth_header: str) -> bool:
        """Verify Payme authentication header.

        Format: Basic base64(Paycom:secret_key)

        Args:
            auth_header: Authorization header value (Basic base64(...))

        Returns:
            True if authentication is valid
        """
        try:
            if not auth_header or not auth_header.startswith("Basic "):
                logger.warning("Invalid authorization header format")
                return False

            # Decode base64 credentials
            encoded_credentials = auth_header.replace("Basic ", "")
            decoded_credentials = base64.b64decode(encoded_credentials).decode()

            # Expected format: "Paycom:{secret_key}"
            expected_credentials = f"Paycom:{self.secret_key}"

            is_valid = decoded_credentials == expected_credentials

            if not is_valid:
                logger.warning("Payme authentication failed")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying Payme auth: {e}", exc_info=True)
            return False

    def build_response(
            self, result: Dict[str, Any] = None, error: Dict[str, Any] = None, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build JSON-RPC 2.0 response.

        Args:
            result: Result data (for success response)
            error: Error data with code and message (for error response)
            request_id: Request ID from the original request

        Returns:
            JSON-RPC 2.0 response dictionary
        """
        response = {}

        if result is not None:
            response["result"] = result
        elif error is not None:
            response["error"] = error

        if request_id is not None:
            response["id"] = request_id

        return response

    def success_response(self, result: Dict[str, Any], request_id: Any = None) -> Dict[str, Any]:
        """Build success response.

        Args:
            result: Result data
            request_id: Request ID

        Returns:
            Success response dictionary
        """
        return self.build_response(result=result, request_id=request_id)

    def error_response(
            self, code: int, message: str, data: Any = None, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build error response.

        Args:
            code: Error code
            message: Error message
            data: Additional error data (optional)
            request_id: Request ID

        Returns:
            Error response dictionary
        """
        error = {"code": code, "message": message}

        if data is not None:
            error["data"] = data

        return self.build_response(error=error, request_id=request_id)

    def check_perform_transaction_response(
            self, allow: bool = True, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build CheckPerformTransaction response.

        Args:
            allow: Whether transaction is allowed
            request_id: Request ID

        Returns:
            CheckPerformTransaction response
        """
        return self.success_response(result={"allow": allow}, request_id=request_id)

    def create_transaction_response(
            self, create_time: int, transaction: str, state: int = 1, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build CreateTransaction response.

        Args:
            create_time: Transaction creation timestamp (milliseconds)
            transaction: Merchant's transaction identifier
            state: Transaction state (default: 1 - created)
            request_id: Request ID

        Returns:
            CreateTransaction response
        """
        return self.success_response(
            result={"create_time": create_time, "transaction": transaction, "state": state},
            request_id=request_id,
        )

    def perform_transaction_response(
            self, transaction: str, perform_time: int, state: int = 2, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build PerformTransaction response.

        Args:
            transaction: Merchant's transaction identifier
            perform_time: Transaction perform timestamp (milliseconds)
            state: Transaction state (default: 2 - completed)
            request_id: Request ID

        Returns:
            PerformTransaction response
        """
        return self.success_response(
            result={"transaction": transaction, "perform_time": perform_time, "state": state},
            request_id=request_id,
        )

    def cancel_transaction_response(
            self, transaction: str, cancel_time: int, state: int, request_id: Any = None
    ) -> Dict[str, Any]:
        """Build CancelTransaction response.

        Args:
            transaction: Merchant's transaction identifier
            cancel_time: Transaction cancel timestamp (milliseconds)
            state: Transaction state (-1 or -2)
            request_id: Request ID

        Returns:
            CancelTransaction response
        """
        return self.success_response(
            result={"transaction": transaction, "cancel_time": cancel_time, "state": state},
            request_id=request_id,
        )

    def check_transaction_response(
            self,
            create_time: int,
            perform_time: int,
            cancel_time: int,
            transaction: str,
            state: int,
            reason: Optional[int] = None,
            request_id: Any = None,
    ) -> Dict[str, Any]:
        """Build CheckTransaction response.

        Args:
            create_time: Transaction creation timestamp (milliseconds)
            perform_time: Transaction perform timestamp (milliseconds, 0 if not performed)
            cancel_time: Transaction cancel timestamp (milliseconds, 0 if not cancelled)
            transaction: Merchant's transaction identifier
            state: Transaction state
            reason: Cancellation reason (optional)
            request_id: Request ID

        Returns:
            CheckTransaction response
        """
        return self.success_response(
            result={
                "create_time": create_time,
                "perform_time": perform_time,
                "cancel_time": cancel_time,
                "transaction": transaction,
                "state": state,
                "reason": reason,
            },
            request_id=request_id,
        )

    def get_statement_response(self, transactions: list, request_id: Any = None) -> Dict[str, Any]:
        """Build GetStatement response.

        Args:
            transactions: List of transaction objects
            request_id: Request ID

        Returns:
            GetStatement response
        """
        return self.success_response(result={"transactions": transactions}, request_id=request_id)

    @staticmethod
    def timestamp_ms() -> int:
        """Get current timestamp in milliseconds.

        Returns:
            Current timestamp in milliseconds
        """
        return int(time.time() * 1000)

    @staticmethod
    def amount_to_tiyin(amount: float) -> int:
        """Convert amount from UZS to tiyin.

        Args:
            amount: Amount in UZS

        Returns:
            Amount in tiyin (1 UZS = 100 tiyin)
        """
        return int(amount * 100)

    @staticmethod
    def tiyin_to_amount(tiyin: int) -> float:
        """Convert amount from tiyin to UZS.

        Args:
            tiyin: Amount in tiyin

        Returns:
            Amount in UZS
        """
        return float(tiyin) / 100
