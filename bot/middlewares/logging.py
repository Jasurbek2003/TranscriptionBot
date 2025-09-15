from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import logging
import time

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging all updates"""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()

        # Log incoming update
        if isinstance(event, Message):
            user = event.from_user
            logger.info(
                f"Message from {user.id} (@{user.username}): "
                f"{event.text[:50] if event.text else 'media/other'}"
            )
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            logger.info(
                f"Callback from {user.id} (@{user.username}): {event.data}"
            )

        try:
            # Process update
            result = await handler(event, data)

            # Log processing time
            processing_time = time.time() - start_time
            if processing_time > 3:  # Log slow requests
                logger.warning(
                    f"Slow request processing: {processing_time:.2f}s for {type(event).__name__}"
                )

            return result

        except Exception as e:
            # Log errors
            logger.error(
                f"Error processing {type(event).__name__}: {str(e)}",
                exc_info=True
            )
            raise
        