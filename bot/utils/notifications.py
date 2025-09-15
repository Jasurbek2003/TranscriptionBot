from aiogram import Bot
from typing import List
import logging

logger = logging.getLogger(__name__)


async def notify_admins_on_startup(bot: Bot, admin_ids: List[int]):
    """Notify admins when bot starts"""
    bot_info = await bot.get_me()

    message = (
        "🚀 <b>Bot Started</b>\n\n"
        f"Bot: @{bot_info.username}\n"
        f"Name: {bot_info.first_name}\n"
        f"ID: {bot_info.id}\n\n"
        "All systems operational!"
    )

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message
            )
            logger.info(f"Notified admin {admin_id} about startup")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


async def notify_admins_on_error(bot: Bot, admin_ids: List[int], error: Exception):
    """Notify admins about critical errors"""
    message = (
        "⚠️ <b>Critical Error</b>\n\n"
        f"Error: {type(error).__name__}\n"
        f"Details: {str(error)[:500]}\n\n"
        "Please check the logs for more information."
    )

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about error: {e}")

