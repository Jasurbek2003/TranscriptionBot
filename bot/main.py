import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from bot.config import settings
from bot.handlers import (
    start,
    media,
    payment,
    wallet,
    history,
    admin,
    errors
)
from bot.middlewares import (
    DatabaseMiddleware,
    AuthMiddleware,
    ThrottlingMiddleware,
    LoggingMiddleware,
    BalanceCheckMiddleware
)
from bot.utils.commands import set_bot_commands
from bot.utils.notifications import notify_admins_on_startup
from core.database import init_database, close_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """Actions to perform on bot startup"""
    logger.info("Starting bot...")

    # Initialize database
    await init_database()
    logger.info("Database initialized")

    # Set bot commands
    await set_bot_commands(bot)
    logger.info("Bot commands set")

    # Notify admins
    await notify_admins_on_startup(bot, settings.ADMIN_IDS)
    logger.info("Admins notified")

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """Actions to perform on bot shutdown"""
    logger.info("Shutting down bot...")

    # Close database connections
    await close_database()
    logger.info("Database connections closed")

    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")

    logger.info("Bot shutdown complete")


async def main():
    """Main bot function"""
    try:
        # Initialize Redis for FSM storage
        redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None
        )
        storage = RedisStorage(redis=redis)

        # Initialize bot
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )

        # Initialize dispatcher
        dp = Dispatcher(storage=storage)

        # Register startup and shutdown handlers
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Register middlewares (order matters!)
        dp.message.middleware(LoggingMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())

        dp.message.middleware(DatabaseMiddleware())
        dp.callback_query.middleware(DatabaseMiddleware())

        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())

        dp.message.middleware(ThrottlingMiddleware())
        dp.callback_query.middleware(ThrottlingMiddleware())

        # Balance check only for media messages
        dp.message.middleware(BalanceCheckMiddleware())

        # Register routers
        dp.include_router(start.router)
        dp.include_router(media.router)
        dp.include_router(payment.router)
        dp.include_router(wallet.router)
        dp.include_router(history.router)
        dp.include_router(admin.router)
        dp.include_router(errors.router)  # Error handler should be last

        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=settings.DROP_PENDING_UPDATES
        )

    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)