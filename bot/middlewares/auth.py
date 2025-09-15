from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from django_admin.apps.users.models import TelegramUser
from django_admin.apps.wallet.models import Wallet
from bot.config import settings
import logging

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

        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        # Check if user exists
        stmt = select(TelegramUser).where(TelegramUser.telegram_id == user_tg.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        # Create new user if doesn't exist
        if not user:
            user = TelegramUser(
                telegram_id=user_tg.id,
                username=user_tg.username or f"user_{user_tg.id}",
                first_name=user_tg.first_name or "",
                last_name=user_tg.last_name or "",
                language_code=user_tg.language_code or settings.DEFAULT_LANGUAGE,
                is_bot=user_tg.is_bot,
                is_premium=user_tg.is_premium or False
            )
            session.add(user)
            await session.flush()

            # Create wallet for new user
            wallet = Wallet(
                user_id=user.id,
                balance=settings.INITIAL_BALANCE,
                currency="UZS"
            )
            session.add(wallet)
            await session.flush()

            logger.info(f"New user registered: {user_tg.id} (@{user_tg.username})")
        else:
            # Update last activity
            user.last_activity = datetime.utcnow()
            await session.flush()

        # Add user to data
        data["user"] = user
        data["wallet"] = await user.get_wallet(session)

        return await handler(event, data)