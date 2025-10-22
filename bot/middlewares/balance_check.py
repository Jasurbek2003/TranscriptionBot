import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.config import settings

logger = logging.getLogger(__name__)


class BalanceCheckMiddleware(BaseMiddleware):
    """Middleware for checking user balance before media processing"""

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
    ) -> Any:
        # Only check for media messages
        if not isinstance(event, Message):
            return await handler(event, data)

        # Check if it's a media message
        media = event.audio or event.video or event.voice or event.video_note
        if not media:
            return await handler(event, data)

        # Get user wallet
        wallet = data.get("wallet")
        if not wallet:
            return await handler(event, data)

        # Calculate estimated cost
        duration_seconds = media.duration if hasattr(media, "duration") else 0
        duration_minutes = (duration_seconds + 59) // 60  # Round up

        is_video = bool(event.video or event.video_note)
        price_per_minute = (
            settings.VIDEO_PRICE_PER_MIN if is_video else settings.AUDIO_PRICE_PER_MIN
        )
        estimated_cost = duration_minutes * price_per_minute

        # Check balance
        if wallet.balance < estimated_cost:
            shortage = estimated_cost - wallet.balance

            await event.answer(
                f"❌ <b>Insufficient balance</b>\n\n"
                f"Duration: {duration_minutes} min\n"
                f"Cost: {estimated_cost:.2f} UZS\n"
                f"Your balance: {wallet.balance:.2f} UZS\n"
                f"Shortage: {shortage:.2f} UZS\n\n"
                f"Please /topup your balance to continue."
            )

            logger.info(
                f"Insufficient balance for user {event.from_user.id}: "
                f"needed {estimated_cost}, has {wallet.balance}"
            )

            return None  # Stop processing

        # Add cost info to data
        data["estimated_cost"] = estimated_cost
        data["duration_minutes"] = duration_minutes

        return await handler(event, data)
