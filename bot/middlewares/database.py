"""
Database middleware for Django ORM

This middleware ensures Django is initialized and handles database operations.
Django ORM is synchronous, so we use sync_to_async for async contexts.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import logging

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware for Django ORM database operations

    Note: Django ORM is synchronous, so handlers should use sync_to_async
    when performing database operations, or we wrap the entire handler.
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        """
        Process the event with Django ORM

        Django automatically handles transactions, so we just call the handler.
        """
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            raise
