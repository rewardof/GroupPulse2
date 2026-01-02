#!/usr/bin/env python3
"""
GroupPulse Main Entry Point

Runs both the Bot (control panel) and Userbot (listener) simultaneously.
"""

import asyncio
import logging
import signal
from typing import Optional

from src.bot.app import GroupPulseBot
from src.userbot.manager import UserbotManager
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class GroupPulseApp:
    """Main application controller."""

    def __init__(self):
        """Initialize application."""
        self.bot: Optional[GroupPulseBot] = None
        self.userbot_manager: Optional[UserbotManager] = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start both bot and userbot services."""
        logger.info("=" * 60)
        logger.info("🚀 Starting GroupPulse")
        logger.info("=" * 60)

        try:
            # Initialize bot
            logger.info("📱 Initializing Bot (Control Panel)...")
            self.bot = GroupPulseBot()

            # Initialize userbot manager
            logger.info("🤖 Initializing Userbot Manager (Listener)...")
            self.userbot_manager = UserbotManager()

            # Start both services
            bot_task = asyncio.create_task(self.bot.start(), name="bot")
            userbot_task = asyncio.create_task(
                self.userbot_manager.start(),
                name="userbot_manager"
            )

            logger.info("=" * 60)
            logger.info("✅ GroupPulse Started Successfully!")
            logger.info("📱 Bot: Running (polling)")
            logger.info("🤖 Userbot: Monitoring active accounts")
            logger.info("=" * 60)

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel tasks
            logger.info("Stopping services...")
            bot_task.cancel()
            userbot_task.cancel()

            # Wait for cancellation
            await asyncio.gather(bot_task, userbot_task, return_exceptions=True)

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop all services gracefully."""
        logger.info("=" * 60)
        logger.info("🛑 Shutting down GroupPulse...")
        logger.info("=" * 60)

        try:
            # Stop userbot manager first (it has active connections)
            if self.userbot_manager:
                logger.info("🤖 Stopping Userbot Manager...")
                await self.userbot_manager.stop()

            # Stop bot
            if self.bot:
                logger.info("📱 Stopping Bot...")
                await self.bot.stop()

            logger.info("=" * 60)
            logger.info("✅ GroupPulse Stopped Successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def shutdown(self):
        """Trigger shutdown."""
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    app = GroupPulseApp()

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        app.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await app.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal")
    finally:
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit(1)
