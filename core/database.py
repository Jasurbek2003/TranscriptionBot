import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool

from bot.config import settings
from core.models import Base
from core.logging import logger

# Global engine and session maker
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def create_engine() -> AsyncEngine:
    """Create async database engine"""
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG_MODE,
        poolclass=NullPool if settings.DEBUG_MODE else None,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {
                "application_name": "TranscriptionBot",
            }
        }
    )


async def init_database() -> None:
    """Initialize database connection and create tables"""
    global _engine, _async_session_maker

    try:
        logger.info("Initializing database connection...")

        # Create engine
        _engine = create_engine()

        # Create session maker
        _async_session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )

        # Create tables
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """Close database connections"""
    global _engine, _async_session_maker

    try:
        if _engine:
            await _engine.dispose()
            _engine = None
            _async_session_maker = None
            logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    if not _async_session_maker:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_engine() -> AsyncEngine:
    """Get database engine"""
    if not _engine:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine


async def health_check() -> bool:
    """Check database health"""
    try:
        async with get_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def create_tables() -> None:
    """Create all tables"""
    if not _engine:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully")


async def drop_tables() -> None:
    """Drop all tables (use with caution!)"""
    if not _engine:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All tables dropped!")


# Utility functions for testing and development
async def reset_database() -> None:
    """Reset database (drop and recreate tables)"""
    logger.warning("Resetting database...")
    await drop_tables()
    await create_tables()
    logger.info("Database reset complete")


async def execute_raw_sql(sql: str, params: dict = None) -> None:
    """Execute raw SQL (use with caution!)"""
    async with get_session() as session:
        await session.execute(sql, params or {})
        await session.commit()