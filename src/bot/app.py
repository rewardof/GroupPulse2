"""
Telegram Bot Application

Main aiogram bot application with handlers and middleware.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from config.settings import settings
from src.bot.handlers import start
import asyncio
import logging

logger = logging.getLogger(__name__)


class GroupPulseBot:
    """
    GroupPulse Telegram Bot.

    Manages bot lifecycle, handlers, and middleware.
    """

    def __init__(self):
        """Initialize bot and dispatcher."""
        # Create bot instance
        self.bot = Bot(
            token=settings.BOT_TOKEN,
        )

        # Create storage (memory for now, can switch to Redis)
        self.storage = MemoryStorage()

        # Create dispatcher
        self.dp = Dispatcher(storage=self.storage)

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all message and callback handlers."""
        # Start and help handlers
        self.dp.include_router(start.router)

        # TODO: Add more handlers when created
        # self.dp.include_router(account.router)
        # self.dp.include_router(groups.router)
        # self.dp.include_router(keywords.router)
        # self.dp.include_router(rules.router)

        logger.info("✓ Bot handlers registered")

    async def start(self):
        """Start the bot (polling mode)."""
        logger.info("Starting GroupPulse Bot...")

        try:
            # Delete webhook if exists
            await self.bot.delete_webhook(drop_pending_updates=True)

            # Get bot info
            me = await self.bot.get_me()
            logger.info(f"✓ Bot started: @{me.username} (ID: {me.id})")

            # Start polling
            await self.dp.start_polling(self.bot)

        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping GroupPulse Bot...")

        try:
            # Close bot session
            await self.bot.session.close()

            # Close storage
            await self.storage.close()

            logger.info("✓ Bot stopped")

        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)


async def main():
    """Main entry point for bot service."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and start bot
    bot_app = GroupPulseBot()

    try:
        await bot_app.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received exit signal")
    finally:
        await bot_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
