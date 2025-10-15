"""Click payment service placeholder."""

from typing import Dict, Any


class ClickService:
    """Placeholder Click payment service."""

    def __init__(self, merchant_id: str, service_id: str, secret_key: str, test_mode: bool = True):
        """Initialize Click service.

        Args:
            merchant_id: Click merchant ID
            service_id: Click service ID
            secret_key: Click secret key
            test_mode: Whether to use test mode
        """
        self.merchant_id = merchant_id
        self.service_id = service_id
        self.secret_key = secret_key
        self.test_mode = test_mode

    async def create_payment(self, amount: float, order_id: str) -> Dict[str, Any]:
        """Create a payment request.

        Args:
            amount: Payment amount
            order_id: Order ID

        Returns:
            Payment creation response
        """
        return {
            "success": False,
            "message": "Click service not implemented",
            "payment_url": None
        }

    async def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Check payment status.

        Args:
            transaction_id: Transaction ID

        Returns:
            Payment status
        """
        return {
            "status": "pending",
            "message": "Click service not implemented"
        }