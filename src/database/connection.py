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
from sqlalchemy.pool import NullPool, QueuePool
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
        logger.info(f"Creating async database engine: {settings.DATABASE_URL.split('@')[1]}")

        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            poolclass=QueuePool if settings.is_production else NullPool,
            # Performance optimizations
            connect_args={
                "server_settings": {
                    "application_name": settings.APP_NAME,
                    "jit": "off",  # Disable JIT for faster simple queries
                }
            },
        )

        logger.info(
            f"Database engine created: pool_size={settings.DB_POOL_SIZE}, "
            f"max_overflow={settings.DB_MAX_OVERFLOW}"
        )

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
        async with get_async_session() as session:
            result = await session.execute("SELECT 1")
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
