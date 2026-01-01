"""
Database Connection Management

Async SQLAlchemy engine and session management with connection pooling.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


# Global async engine instance
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create async database engine (singleton pattern).

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _async_engine

    if _async_engine is None:
        # Safe database URL logging (hide password)
        if '@' in settings.DATABASE_URL:
            safe_url = settings.DATABASE_URL.split('@')[1]
        else:
            safe_url = "local database"

        logger.info(f"Creating async database engine: {safe_url}")

        # Determine if using PostgreSQL or SQLite
        is_postgres = settings.DATABASE_URL.startswith('postgresql')

        # Base engine arguments
        engine_args = {
            "echo": settings.DB_ECHO,
            "poolclass": NullPool,  # Required for async engines
        }

        # PostgreSQL-specific settings
        if is_postgres:
            engine_args.update({
                "pool_pre_ping": True,
                "connect_args": {
                    "server_settings": {
                        "application_name": settings.APP_NAME,
                        "jit": "off",
                    }
                },
            })

        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_args
        )

        logger.info(f"Database engine created (async with NullPool)")

    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create async session factory (singleton pattern).

    Returns:
        async_sessionmaker: Session factory for creating async sessions
    """
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine()

        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit (better for async)
            autoflush=False,  # Manual flush for better control
            autocommit=False,
        )

        logger.info("Async session factory created")

    return _async_session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for async database sessions.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(select(User))

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_async_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def health_check() -> bool:
    """
    Check database connection health.

    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        from sqlalchemy import text
        async with get_async_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_async_engine():
    """Close async engine and cleanup connections."""
    global _async_engine, _async_session_factory

    if _async_engine:
        logger.info("Closing database engine...")
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Database engine closed")
