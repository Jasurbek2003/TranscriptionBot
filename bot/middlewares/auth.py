"""
Authentication middleware using Django ORM

This middleware handles user registration and authentication using Django models.
"""

from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async
from django.utils import timezone
import logging

# Import Django models
from bot.django_setup import TelegramUser, Wallet
from bot.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and registration"""

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # Skip if not a message or callback query
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user_tg = event.from_user
        if not user_tg:
            return await handler(event, data)

        # Get or create user (Django ORM)
        user, wallet = await self._get_or_create_user(user_tg)

        # Add user and wallet to data
        data["user"] = user
        data["wallet"] = wallet

        return await handler(event, data)

    @sync_to_async
    def _get_or_create_user(self, user_tg):
        """Get or create user and wallet using Django ORM"""
        try:
            # Try to get existing user
            user = TelegramUser.objects.get(telegram_id=user_tg.id)

            # Update last activity
            user.last_activity = timezone.now()
            user.save(update_fields=['last_activity'])

            # Get wallet
            wallet = Wallet.objects.get(user=user)

        except TelegramUser.DoesNotExist:
            # Create new user
            user = TelegramUser.objects.create(
                telegram_id=user_tg.id,
                username=user_tg.username or f"user_{user_tg.id}",
                first_name=user_tg.first_name or "",
                last_name=user_tg.last_name or "",
                language_code=user_tg.language_code or settings.default_language.value,
                is_bot=user_tg.is_bot,
                is_premium=user_tg.is_premium or False,
            )

            # Create wallet for new user
            wallet = Wallet.objects.create(
                user=user,
                balance=settings.pricing.initial_balance,
                currency="UZS"
            )

            logger.info(f"New user registered: {user_tg.id} (@{user_tg.username})")

        except Wallet.DoesNotExist:
            # Create wallet if missing (shouldn't happen, but just in case)
            wallet = Wallet.objects.create(
                user=user,
                balance=settings.pricing.initial_balance,
                currency="UZS"
            )
            logger.warning(f"Created missing wallet for user {user.telegram_id}")

        return user, wallet
