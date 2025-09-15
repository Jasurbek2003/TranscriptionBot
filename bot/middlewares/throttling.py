from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from redis.asyncio import Redis
from bot.config import settings
import logging

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting"""

    def __init__(self, redis: Redis = None):
        self.redis = redis
        self.default_rate = settings.THROTTLE_MAX_MESSAGES
        self.window = settings.THROTTLE_TIME_WINDOW
        self.media_rate = settings.THROTTLE_MAX_MEDIA

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        # Skip throttling for admins
        if user.id in settings.ADMIN_IDS:
            return await handler(event, data)

        # Check if redis is available
        if not self.redis:
            return await handler(event, data)

        # Determine rate limit based on message type
        is_media = bool(event.audio or event.video or event.voice or event.video_note)
        rate_limit = self.media_rate if is_media else self.default_rate
        key_suffix = "media" if is_media else "message"

        # Create rate limit key
        key = f"throttle:{user.id}:{key_suffix}"

        try:
            # Get current count
            count = await self.redis.incr(key)

            # Set expiry on first message
            if count == 1:
                await self.redis.expire(key, self.window)

            # Check if rate limit exceeded
            if count > rate_limit:
                # Get TTL for the key
                ttl = await self.redis.ttl(key)

                # Send warning message
                await event.answer(
                    f"⚠️ Too many requests! Please wait {ttl} seconds before sending another message.",
                    show_alert=True if hasattr(event, 'answer') else False
                )

                logger.warning(f"Rate limit exceeded for user {user.id} (@{user.username})")
                return None

        except Exception as e:
            logger.error(f"Throttling middleware error: {e}")

        return await handler(event, data)