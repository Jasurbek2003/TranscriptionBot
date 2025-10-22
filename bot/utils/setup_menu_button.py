#!/usr/bin/env python3
"""
Script to setup Telegram Bot Menu Button with WebApp
This sets the persistent menu button that appears in the chat input area
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo

from bot.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_menu_button():
    """Setup menu button for the bot"""
    bot = Bot(token=settings.bot_token)

    try:
        # Set menu button with webapp
        menu_button = MenuButtonWebApp(
            text="Open Web App", web_app=WebAppInfo(url=settings.webapp_url)
        )

        await bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Menu button set successfully with URL: {settings.webapp_url}")

        # Also set bot commands
        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="Show help information"),
            BotCommand(command="webapp", description="Open web application"),
            BotCommand(command="balance", description="Check your balance"),
            BotCommand(command="transcribe", description="Transcription guide"),
            BotCommand(command="status", description="Bot status"),
            BotCommand(command="support", description="Get support"),
        ]

        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("✅ Bot commands updated")

        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username}")
        logger.info(f"✅ WebApp URL: {settings.webapp_url}")

    except Exception as e:
        logger.error(f"❌ Error setting menu button: {e}")
        raise
    finally:
        await bot.session.close()


async def remove_menu_button():
    """Remove menu button (reset to default)"""
    bot = Bot(token=settings.bot_token)

    try:
        from aiogram.types import MenuButtonDefault

        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        logger.info("✅ Menu button removed (reset to default)")

    except Exception as e:
        logger.error(f"❌ Error removing menu button: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup Telegram Bot Menu Button")
    parser.add_argument(
        "--remove", action="store_true", help="Remove the menu button instead of setting it"
    )

    args = parser.parse_args()

    if args.remove:
        logger.info("Removing menu button...")
        asyncio.run(remove_menu_button())
    else:
        logger.info("Setting up menu button...")
        asyncio.run(setup_menu_button())
