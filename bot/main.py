import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Initialize Django
from bot.django_setup import *

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
# from aiogram.fsm.storage.redis import RedisStorage
# from redis.asyncio import Redis

from bot.config import settings
from bot.handlers import (
    start,
    media,
    balance,
    payment,
    # wallet,
    # history,
    # admin,  # Commented out - needs Django ORM refactoring
    errors
)
from bot.handlers import webapp  # Import webapp handler
from bot.middlewares import (
    DatabaseMiddleware,
    AuthMiddleware,
    # ThrottlingMiddleware,
    # LoggingMiddleware,
    # BalanceCheckMiddleware
)
from bot.utils.commands import set_bot_commands
from bot.utils.notifications import notify_admins_on_startup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """Actions to perform on bot startup"""
    logger.info("Starting bot...")

    # Django database is already initialized
    logger.info("Using Django ORM database")

    # Set bot commands
    await set_bot_commands(bot)
    logger.info("Bot commands set")

    # Notify admins
    await notify_admins_on_startup(bot, settings.admin_ids)
    logger.info("Admins notified")

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """Actions to perform on bot shutdown"""
    logger.info("Shutting down bot...")

    # Django handles database connections automatically
    logger.info("Django ORM cleanup complete")

    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")

    logger.info("Bot shutdown complete")


async def main():
    """Main bot function"""
    try:
        # Initialize Memory storage for FSM (development mode)
        storage = MemoryStorage()

        # Redis storage (disabled for development)
        # redis = Redis(
        #     host=settings.redis.host,
        #     port=settings.redis.port,
        #     db=settings.redis.db,
        #     password=settings.redis.password if settings.redis.password else None
        # )
        # storage = RedisStorage(redis=redis)

        # Initialize bot with custom API server if configured
        if settings.bot_api_server:
            logger.info(f"Using custom Bot API server: {settings.bot_api_server}")
            api = TelegramAPIServer.from_base(settings.bot_api_server)
            session = AiohttpSession(api=api)
            bot = Bot(
                token=settings.bot_token,
                session=session,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.HTML
                )
            )
        else:
            logger.info("Using standard Telegram Bot API")
            bot = Bot(
                token=settings.bot_token,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.HTML
                )
            )

        # Initialize dispatcher
        dp = Dispatcher(storage=storage)

        # Register startup and shutdown handlers
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Register middlewares
        # Database middleware - provides session
        dp.message.middleware(DatabaseMiddleware())
        dp.callback_query.middleware(DatabaseMiddleware())

        # Auth middleware - handles user registration and authentication
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())

        # Additional middlewares (disabled for now)
        # dp.message.middleware(LoggingMiddleware())
        # dp.callback_query.middleware(LoggingMiddleware())
        # dp.message.middleware(ThrottlingMiddleware())
        # dp.callback_query.middleware(ThrottlingMiddleware())
        # dp.message.middleware(BalanceCheckMiddleware())

        # Register routers (media router first to handle transcription properly)
        dp.include_router(webapp.router)  # Webapp handler
        dp.include_router(media.router)
        dp.include_router(payment.router)  # Payment handlers with Click and Payme
        dp.include_router(balance.router)
        dp.include_router(start.router)
        # dp.include_router(wallet.router)
        # dp.include_router(history.router)
        # dp.include_router(admin.router)
        dp.include_router(errors.router)  # Error handler should be last

        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=settings.drop_pending_updates
        )

    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Fix for Windows event loop issue with aiodns
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)