from typing import Any, Dict, Union

from aiogram.filters import Filter
from aiogram.types import Message

from bot.config import settings


class MediaFilter(Filter):
    """Filter for media messages (audio or video)"""

    async def __call__(self, message: Message) -> bool:
        return bool(message.audio or message.video or message.voice or message.video_note)


class AudioFilter(Filter):
    """Filter for audio messages"""

    def __init__(self, check_duration: bool = True, max_duration: int = None):
        self.check_duration = check_duration
        self.max_duration = max_duration or settings.ai.max_audio_duration_seconds

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        if not (message.audio or message.voice):
            return False

        media = message.audio or message.voice

        if self.check_duration and media.duration > self.max_duration:
            return False

        return {
            "media_type": "audio",
            "duration": media.duration,
            "file_id": media.file_id,
            "file_size": media.file_size,
        }


class VideoFilter(Filter):
    """Filter for video messages"""

    def __init__(self, check_duration: bool = True, max_duration: int = None):
        self.check_duration = check_duration
        self.max_duration = max_duration or settings.ai.max_video_duration_seconds

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        if not (message.video or message.video_note):
            return False

        media = message.video or message.video_note

        if self.check_duration and media.duration > self.max_duration:
            return False

        return {
            "media_type": "video",
            "duration": media.duration,
            "file_id": media.file_id,
            "file_size": media.file_size,
        }


class FileSizeFilter(Filter):
    """Filter for checking file size"""

    def __init__(self, max_size_mb: int = None):
        self.max_size_bytes = (max_size_mb or settings.ai.max_file_size_mb) * 1024 * 1024

    async def __call__(self, message: Message) -> bool:
        media = message.audio or message.video or message.voice or message.video_note

        if not media:
            return False

        if media.file_size and media.file_size > self.max_size_bytes:
            return False

        return True


class BalanceFilter(Filter):
    """Filter to check if user has sufficient balance for transcription"""

    async def __call__(self, message: Message, user, wallet) -> Union[bool, Dict[str, Any]]:
        """
        Check if user has sufficient balance
        Note: user and wallet are injected by the auth middleware
        """
        if not user or not wallet:
            await message.answer(
                "❌ <b>Authentication Error</b>\n\n"
                "Please restart the bot with /start to authenticate."
            )
            return False

        # Get media info
        media = message.audio or message.video or message.voice or message.video_note
        if not media:
            return False

        # Determine media type and calculate minimum cost
        if message.audio or message.voice:
            price_per_min = settings.pricing.audio_price_per_min
        else:
            price_per_min = settings.pricing.video_price_per_min

        # Calculate minimum cost (1 minute)
        min_cost = price_per_min

        # Check balance
        if wallet.balance < min_cost:
            await message.answer(
                f"❌ <b>Insufficient Balance</b>\n\n"
                f"Minimum required: {min_cost:.2f} UZS\n"
                f"Your balance: {wallet.balance:.2f} UZS\n\n"
                f"Please use /topup to add funds to your account."
            )
            return False

        return True
