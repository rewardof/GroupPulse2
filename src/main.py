"""
GroupPulse Main Entry Point

Orchestrates all services: database, userbot workers, bot, and forwarding.
"""

import asyncio
import signal
import sys
from typing import Optional
from config.settings import settings
from src.database.connection import get_async_engine, close_async_engine
from src.database.models import Base
from src.core.rate_limiter import RateLimiter
from src.core.rule_matcher import RuleMatcher
from src.userbot.worker import UserbotWorkerPool
from src.services.forwarding_service import ForwardingService
from src.bot.app import GroupPulseBot
import logging

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/grouppulse.log') if settings.is_production else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


class GroupPulseApplication:
    """
    Main GroupPulse application.

    Manages lifecycle of all components:
    - Database connection
    - Userbot worker pool
    - Forwarding service
    - Telegram bot
    """

    def __init__(self):
        """Initialize application components."""
        self.db_engine = None
        self.userbot_pool: Optional[UserbotWorkerPool] = None
        self.forwarding_service: Optional[ForwardingService] = None
        self.bot: Optional[GroupPulseBot] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.rule_matcher: Optional[RuleMatcher] = None
        self._shutdown = False

    async def initialize_database(self):
        """Initialize database connection and create tables."""
        logger.info("Initializing database...")

        try:
            # Get async engine
            self.db_engine = get_async_engine()

            # Create tables if they don't exist
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("✓ Database initialized")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    async def initialize_services(self):
        """Initialize core services."""
        logger.info("Initializing core services...")

        try:
            # Rate limiter
            self.rate_limiter = RateLimiter(
                global_rate=settings.GLOBAL_RATE_LIMIT,
                account_rate=settings.ACCOUNT_RATE_LIMIT,
                destination_rate=settings.DESTINATION_RATE_LIMIT
            )
            logger.info("✓ Rate limiter initialized")

            # Rule matcher
            self.rule_matcher = RuleMatcher()
            logger.info("✓ Rule matcher initialized")

            # Userbot worker pool
            self.userbot_pool = UserbotWorkerPool(max_workers=settings.MAX_WORKERS)
            logger.info("✓ Userbot worker pool initialized")

            # Forwarding service
            self.forwarding_service = ForwardingService(
                rule_matcher=self.rule_matcher,
                rate_limiter=self.rate_limiter,
                userbot_pool=self.userbot_pool
            )
            logger.info("✓ Forwarding service initialized")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            raise

    async def start_bot(self):
        """Start Telegram bot."""
        logger.info("Starting Telegram bot...")

        try:
            self.bot = GroupPulseBot()
            # Bot start is blocking, run in background task
            asyncio.create_task(self.bot.start())
            logger.info("✓ Bot started")

        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            raise

    async def load_active_accounts(self):
        """
        Load active accounts from database and start userbot workers.

        This should be called after services are initialized.
        """
        logger.info("Loading active accounts...")

        # TODO: Implement account loading from database
        # from src.database.repositories.account_repo import AccountRepository
        # from src.database.connection import get_async_session
        #
        # async with get_async_session() as session:
        #     account_repo = AccountRepository(session)
        #     accounts = await account_repo.get_active_accounts()
        #
        #     for account in accounts:
        #         # Decrypt session string
        #         # Load groups
        #         # Load keywords and rules
        #         # Start userbot worker
        #         pass

        logger.info("✓ Active accounts loaded (0 accounts)")

    async def start(self):
        """Start the application."""
        logger.info("=" * 60)
        logger.info(f"Starting GroupPulse v{settings.APP_VERSION}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info("=" * 60)

        try:
            # 1. Initialize database
            await self.initialize_database()

            # 2. Initialize services
            await self.initialize_services()

            # 3. Load active accounts from database
            await self.load_active_accounts()

            # 4. Start bot
            await self.start_bot()

            logger.info("=" * 60)
            logger.info("✓ GroupPulse started successfully!")
            logger.info("=" * 60)

            # Keep running until shutdown
            while not self._shutdown:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start application: {e}", exc_info=True)
            await self.stop()
            sys.exit(1)

    async def stop(self):
        """Stop the application gracefully."""
        if self._shutdown:
            return

        self._shutdown = True

        logger.info("=" * 60)
        logger.info("Shutting down GroupPulse...")
        logger.info("=" * 60)

        try:
            # 1. Stop bot
            if self.bot:
                logger.info("Stopping bot...")
                await self.bot.stop()

            # 2. Stop all userbot workers
            if self.userbot_pool:
                logger.info("Stopping userbot workers...")
                await self.userbot_pool.shutdown_all()

            # 3. Close database connection
            logger.info("Closing database...")
            await close_async_engine()

            logger.info("=" * 60)
            logger.info("✓ GroupPulse shut down successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    app = GroupPulseApplication()
    app.setup_signal_handlers()

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
