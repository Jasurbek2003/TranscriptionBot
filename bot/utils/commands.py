from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from bot.config import settings
import logging

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Set bot commands for menu"""

    # Default commands for all users
    default_commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="menu", description="Show main menu"),
        BotCommand(command="balance", description="Check balance"),
        BotCommand(command="topup", description="Top up balance"),
        BotCommand(command="history", description="Transaction history"),
        BotCommand(command="transcribe", description="Send media for transcription"),
        BotCommand(command="settings", description="Bot settings"),
        BotCommand(command="support", description="Contact support"),
    ]

    # Admin commands
    admin_commands = default_commands + [
        BotCommand(command="admin", description="Admin panel"),
        BotCommand(command="stats", description="Bot statistics"),
        BotCommand(command="broadcast", description="Send broadcast"),
        BotCommand(command="users", description="User management"),
    ]

    try:
        # Set default commands for all users
        await bot.set_my_commands(
            commands=default_commands,
            scope=BotCommandScopeDefault()
        )

        # Set admin commands for admin users
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.set_my_commands(
                    commands=admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except Exception as e:
                logger.error(f"Failed to set admin commands for {admin_id}: {e}")

        logger.info("Bot commands set successfully")

    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
