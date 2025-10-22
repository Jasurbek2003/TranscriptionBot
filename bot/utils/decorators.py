"""Decorators for bot handlers."""

import logging
from functools import wraps
from typing import Any, Callable

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings
from core.enums import UserRole

logger = logging.getLogger(__name__)


def user_required(func: Callable) -> Callable:
    """Decorator to ensure user is authenticated."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        try:
            # Get user from context (should be set by middleware)
            user = context.user_data.get("user")

            if not user:
                # Try to get user info from update
                telegram_user = update.effective_user
                if not telegram_user:
                    logger.warning("No user information in update")
                    return

                # Try to find user in database
                from django_admin.apps.users.models import User

                try:
                    user = User.objects.get(telegram_id=telegram_user.id)
                    context.user_data["user"] = user
                except User.DoesNotExist:
                    # Create new user if needed
                    user = User.objects.create(
                        telegram_id=telegram_user.id,
                        username=telegram_user.username,
                        first_name=telegram_user.first_name,
                        last_name=telegram_user.last_name,
                        role=UserRole.USER,
                    )
                    context.user_data["user"] = user
                    logger.info(f"Created new user: {user.telegram_id}")

            # Check if user is blocked
            if user.status == "blocked":
                if update.message:
                    await update.message.reply_text(
                        "❌ Your account has been blocked. Please contact support."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "Your account has been blocked. Please contact support.", show_alert=True
                    )
                return

            return await func(update, context, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in user_required decorator: {e}")
            error_message = "❌ An error occurred. Please try again."

            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)

    return wrapper


def admin_required(func: Callable) -> Callable:
    """Decorator to ensure user is admin."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        try:
            telegram_user = update.effective_user
            if not telegram_user:
                logger.warning("No user information in update")
                return

            # Check if user is in admin list
            if telegram_user.id not in settings.admin_ids:
                if update.message:
                    await update.message.reply_text("❌ Access denied. Admin rights required.")
                elif update.callback_query:
                    await update.callback_query.answer("Access denied", show_alert=True)
                return

            # Get user from database
            from django_admin.apps.users.models import User

            try:
                user = User.objects.get(telegram_id=telegram_user.id)
            except User.DoesNotExist:
                # Create admin user if doesn't exist
                user = User.objects.create(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    role=UserRole.ADMIN,
                )
                logger.info(f"Created new admin user: {user.telegram_id}")

            context.user_data["user"] = user

            return await func(update, context, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in admin_required decorator: {e}")
            error_message = "❌ An error occurred. Please try again."

            if update.message:
                await update.message.reply_text(error_message)
            elif update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)

    return wrapper


def maintenance_check(func: Callable) -> Callable:
    """Decorator to check if bot is in maintenance mode."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        if settings.maintenance_mode:
            telegram_user = update.effective_user

            # Allow admins to use bot during maintenance
            if telegram_user and telegram_user.id in settings.admin_ids:
                return await func(update, context, *args, **kwargs)

            maintenance_message = (
                "🛠 <b>Maintenance Mode</b>\n\n"
                "The bot is currently under maintenance. "
                "Please try again later.\n\n"
                "Sorry for the inconvenience."
            )

            if update.message:
                await update.message.reply_text(maintenance_message, parse_mode="HTML")
            elif update.callback_query:
                await update.callback_query.answer("Bot is under maintenance", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


def rate_limit(max_calls: int = 5, window_seconds: int = 60):
    """Rate limiting decorator."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ) -> Any:
            telegram_user = update.effective_user
            if not telegram_user:
                return await func(update, context, *args, **kwargs)

            # Skip rate limiting for admins
            if telegram_user.id in settings.admin_ids:
                return await func(update, context, *args, **kwargs)

            # Implement rate limiting logic here
            # This is a simplified version - in production, use Redis
            user_calls = context.user_data.get("rate_limit_calls", [])
            current_time = (
                update.message.date if update.message else update.callback_query.message.date
            )

            # Remove old calls outside the window
            user_calls = [
                call_time
                for call_time in user_calls
                if (current_time - call_time).total_seconds() < window_seconds
            ]

            if len(user_calls) >= max_calls:
                if update.message:
                    await update.message.reply_text(
                        f"⏰ Rate limit exceeded. Please wait {window_seconds} seconds between requests."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "Rate limit exceeded. Please slow down.", show_alert=True
                    )
                return

            # Add current call
            user_calls.append(current_time)
            context.user_data["rate_limit_calls"] = user_calls

            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator


def log_user_action(action: str):
    """Decorator to log user actions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ) -> Any:
            try:
                telegram_user = update.effective_user
                if telegram_user:
                    logger.info(f"User {telegram_user.id} performed action: {action}")

                return await func(update, context, *args, **kwargs)

            except Exception as e:
                if telegram_user:
                    logger.error(f"Error in action {action} for user {telegram_user.id}: {e}")
                else:
                    logger.error(f"Error in action {action}: {e}")
                raise

        return wrapper

    return decorator
