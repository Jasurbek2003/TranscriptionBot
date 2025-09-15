from aiogram.filters import Filter
from aiogram.types import CallbackQuery
import re


class PaymentCallbackFilter(Filter):
    """Filter for payment-related callbacks"""

    def __init__(self, payment_type: str = None):
        self.payment_type = payment_type
        self.pattern = re.compile(r"payment:(\w+)(?::(.+))?")

    async def __call__(self, callback: CallbackQuery) -> bool:
        if not callback.data:
            return False

        match = self.pattern.match(callback.data)
        if not match:
            return False

        if self.payment_type:
            return match.group(1) == self.payment_type

        return True