"""Click payment gateway integration service.

Click Uzbekistan payment system integration using SHOP API.
Official Documentation: https://docs.click.uz/
"""

from typing import Dict, Any, Optional
import hashlib
import logging
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)


class ClickService:
    """Click payment gateway service implementing SHOP API specification.

    Click uses a two-step payment process:
    1. Prepare (action=0): Validate and reserve the transaction
    2. Complete (action=1): Confirm and execute the payment
    """

    # Click error codes based on official documentation
    ERROR_CODES = {
        "SUCCESS": 0,
        "SIGN_CHECK_FAILED": -1,
        "INVALID_AMOUNT": -2,
        "ACTION_NOT_FOUND": -3,
        "ALREADY_PAID": -4,
        "USER_DOES_NOT_EXIST": -5,
        "TRANSACTION_DOES_NOT_EXIST": -6,
        "FAILED_TO_UPDATE_USER": -7,
        "ERROR_IN_REQUEST_FROM_CLICK": -8,
        "TRANSACTION_CANCELLED": -9,
    }

    def __init__(
        self,
        merchant_id: str,
        service_id: str,
        secret_key: str,
        merchant_user_id: str = None,
        test_mode: bool = True
    ):
        """Initialize Click service.

        Args:
            merchant_id: Click merchant ID
            service_id: Click service ID
            secret_key: Click secret key for signature verification
            merchant_user_id: Click merchant user ID (for Merchant API)
            test_mode: Whether to use test mode
        """
        self.merchant_id = merchant_id
        self.service_id = service_id
        self.secret_key = secret_key
        self.merchant_user_id = merchant_user_id
        self.test_mode = test_mode

        # Click URLs
        self.checkout_url = (
            "https://my.click.uz/services/pay"
            if not test_mode
            else "https://test.click.uz/services/pay"
        )
        self.api_url = "https://api.click.uz/v2/merchant"

    def create_payment_link(
        self,
        amount: float,
        order_id: str,
        return_url: Optional[str] = None
    ) -> str:
        """Create a payment link for user to complete payment.

        Args:
            amount: Payment amount in UZS
            order_id: Unique order/transaction ID (merchant_trans_id)
            return_url: URL to redirect after payment

        Returns:
            Payment URL string
        """
        try:
            params = {
                "service_id": self.service_id,
                "merchant_id": self.merchant_id,
                "amount": f"{amount:.2f}",
                "transaction_param": order_id,  # This becomes merchant_trans_id
            }

            if return_url:
                params["return_url"] = return_url

            payment_url = f"{self.checkout_url}?{urlencode(params)}"

            logger.info(
                f"Created Click payment link for order {order_id}, "
                f"amount: {amount} UZS"
            )
            return payment_url

        except Exception as e:
            logger.error(f"Error creating Click payment link: {e}", exc_info=True)
            return ""

    def verify_signature(
        self,
        click_trans_id: str,
        service_id: str,
        merchant_trans_id: str,
        amount: str,
        action: str,
        sign_time: str,
        sign_string: str,
        merchant_prepare_id: str = None
    ) -> bool:
        """Verify Click webhook signature.

        Signature algorithm (MD5):
        - For Prepare (action=0):
          MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
        - For Complete (action=1):
          MD5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)

        Args:
            click_trans_id: Click transaction ID
            service_id: Service ID
            merchant_trans_id: Merchant transaction ID
            amount: Payment amount
            action: Action type (0=prepare, 1=complete)
            sign_time: Signature timestamp
            sign_string: Provided signature
            merchant_prepare_id: Merchant prepare ID (required for Complete)

        Returns:
            True if signature is valid
        """
        try:
            # Build signature string based on action
            if action == "0":  # Prepare
                signature_str = (
                    f"{click_trans_id}{service_id}{self.secret_key}"
                    f"{merchant_trans_id}{amount}{action}{sign_time}"
                )
            elif action == "1":  # Complete
                if not merchant_prepare_id:
                    logger.warning("merchant_prepare_id is required for Complete action")
                    return False
                signature_str = (
                    f"{click_trans_id}{service_id}{self.secret_key}"
                    f"{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
                )
            else:
                logger.warning(f"Unknown action: {action}")
                return False

            # Calculate MD5 hash
            calculated_sign = hashlib.md5(signature_str.encode()).hexdigest()

            is_valid = calculated_sign == sign_string

            if not is_valid:
                logger.warning(
                    f"Click signature verification failed for transaction {merchant_trans_id}. "
                    f"Expected: {calculated_sign}, Got: {sign_string}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying Click signature: {e}", exc_info=True)
            return False

    def build_response(
        self,
        error: int,
        error_note: str,
        click_trans_id: str = None,
        merchant_trans_id: str = None,
        merchant_prepare_id: str = None,
        merchant_confirm_id: str = None
    ) -> Dict[str, Any]:
        """Build Click webhook response.

        Args:
            error: Error code (0 for success)
            error_note: Error description
            click_trans_id: Click transaction ID
            merchant_trans_id: Merchant transaction ID
            merchant_prepare_id: Merchant prepare ID (for Prepare response)
            merchant_confirm_id: Merchant confirm ID (for Complete response)

        Returns:
            Response dictionary
        """
        response = {
            "error": error,
            "error_note": error_note,
        }

        if click_trans_id:
            response["click_trans_id"] = click_trans_id
        if merchant_trans_id:
            response["merchant_trans_id"] = merchant_trans_id
        if merchant_prepare_id:
            response["merchant_prepare_id"] = merchant_prepare_id
        if merchant_confirm_id:
            response["merchant_confirm_id"] = merchant_confirm_id

        return response

    def prepare_response(
        self,
        click_trans_id: str,
        merchant_trans_id: str,
        merchant_prepare_id: int,
        error: int = 0,
        error_note: str = "Success"
    ) -> Dict[str, Any]:
        """Build response for Prepare action.

        Args:
            click_trans_id: Click transaction ID
            merchant_trans_id: Merchant transaction ID
            merchant_prepare_id: Database transaction ID
            error: Error code (default: 0 - success)
            error_note: Error description (default: "Success")

        Returns:
            Prepare response dictionary
        """
        return self.build_response(
            error=error,
            error_note=error_note,
            click_trans_id=click_trans_id,
            merchant_trans_id=merchant_trans_id,
            merchant_prepare_id=str(merchant_prepare_id)
        )

    def complete_response(
        self,
        click_trans_id: str,
        merchant_trans_id: str,
        merchant_confirm_id: int,
        error: int = 0,
        error_note: str = "Success"
    ) -> Dict[str, Any]:
        """Build response for Complete action.

        Args:
            click_trans_id: Click transaction ID
            merchant_trans_id: Merchant transaction ID
            merchant_confirm_id: Database transaction ID
            error: Error code (default: 0 - success)
            error_note: Error description (default: "Success")

        Returns:
            Complete response dictionary
        """
        return self.build_response(
            error=error,
            error_note=error_note,
            click_trans_id=click_trans_id,
            merchant_trans_id=merchant_trans_id,
            merchant_confirm_id=str(merchant_confirm_id)
        )

    def error_response(
        self,
        error: int,
        error_note: str
    ) -> Dict[str, Any]:
        """Build error response.

        Args:
            error: Error code
            error_note: Error description

        Returns:
            Error response dictionary
        """
        return self.build_response(error=error, error_note=error_note)

    def get_auth_header(self, timestamp: int = None) -> str:
        """Generate authentication header for Merchant API requests.

        Format: Auth: merchant_user_id:digest:timestamp
        where digest = SHA1(timestamp + secret_key)

        Args:
            timestamp: UNIX timestamp (10 digits). If None, current time is used.

        Returns:
            Authentication header value
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate digest: SHA1(timestamp + secret_key)
        digest_str = f"{timestamp}{self.secret_key}"
        digest = hashlib.sha1(digest_str.encode()).hexdigest()

        auth_header = f"{self.merchant_user_id}:{digest}:{timestamp}"

        return auth_header