#!/usr/bin/env python3
"""
Script to update Telegram Bot Commands
This updates the command list that appears in the bot menu
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging

from aiogram import Bot

from bot.config import settings
from bot.utils.commands import set_bot_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_bot_commands():
    """Update bot commands"""
    bot = Bot(token=settings.bot_token)

    try:
        logger.info("Updating bot commands...")

        # Use the existing set_bot_commands function
        await set_bot_commands(bot)

        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")
        logger.info("✅ Commands updated successfully!")

        # List the commands
        from aiogram.types import BotCommandScopeDefault

        commands = await bot.get_my_commands(scope=BotCommandScopeDefault())

        logger.info("\n📝 Available commands:")
        for cmd in commands:
            logger.info(f"  /{cmd.command} - {cmd.description}")

    except Exception as e:
        logger.error(f"❌ Error updating commands: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Telegram Bot Commands Update")
    logger.info("=" * 50)

    asyncio.run(update_bot_commands())

    logger.info("\n" + "=" * 50)
    logger.info("✨ Done! Commands updated successfully.")
    logger.info("=" * 50)
