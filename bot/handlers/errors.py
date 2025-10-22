import logging

from aiogram import Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router()


@router.error()
async def error_handler(event: ErrorEvent):
    """Global error handler"""
    exception = event.exception

    if isinstance(exception, TelegramBadRequest):
        logger.error(f"Bad request: {exception}")
    elif isinstance(exception, TelegramNotFound):
        logger.error(f"Not found: {exception}")
    elif isinstance(exception, TelegramRetryAfter):
        logger.warning(f"Rate limited, retry after {exception.retry_after}s")
    elif isinstance(exception, TelegramForbiddenError):
        logger.warning(f"Forbidden: {exception}")
    else:
        logger.error(f"Unhandled error: {exception}", exc_info=True)

    # Try to notify user about error
    if event.update.message:
        try:
            await event.update.message.answer(
                "❌ An error occurred while processing your request. " "Please try again later."
            )
        except Exception as e:
            # Last resort error handler - log but don't raise
            logger.error(f"Failed to send error message to user: {e}")
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer(
                "❌ An error occurred. Please try again.", show_alert=True
            )
        except Exception as e:
            # Last resort error handler - log but don't raise
            logger.error(f"Failed to send error callback to user: {e}")
