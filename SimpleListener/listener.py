#!/usr/bin/env python3
"""
Simple Telegram Message Listener with Rate Limiter

Listens to all groups and forwards matching messages to a destination group.
Uses rate limiting to prevent FloodWait errors.
"""

import asyncio
import logging
import time
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ==================== CONFIGURATION ====================

# Telegram API credentials
API_ID = 28524826
API_HASH = "7f2ce73d335735fe428df68cd6de48db"
SESSION_STRING = ""  # Leave empty for first run, will be generated

# Destination group (where to forward messages)
DESTINATION_GROUP_ID = -1001234567890  # Replace with your group ID

# Keywords to match (case-insensitive)
KEYWORDS = ["python", "telethon", "bot"]

# Rate limiting (messages per second)
RATE_LIMIT = 5  # Max 5 messages per second

# =======================================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Messages per second
        """
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a token is available."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class SimpleListener:
    """Simple message listener with rate limiting."""

    def __init__(self):
        """Initialize listener."""
        self.client = None
        self.rate_limiter = RateLimiter(RATE_LIMIT)
        self.destination_entity = None

    async def start(self):
        """Start the listener."""
        logger.info("=" * 60)
        logger.info("🚀 Starting Simple Message Listener")
        logger.info("=" * 60)

        # Create client
        self.client = TelegramClient(
            StringSession(SESSION_STRING),
            API_ID,
            API_HASH,
            connection_retries=10,
            retry_delay=3,
            timeout=30,
            auto_reconnect=True,
        )

        await self.client.connect()

        # Check authorization
        if not await self.client.is_user_authorized():
            logger.error("❌ Not authorized! Run login.py first to generate session.")
            return

        # Get user info
        me = await self.client.get_me()
        logger.info(f"✅ Logged in as: {me.first_name} (@{me.username})")

        # Cache destination entity
        try:
            self.destination_entity = await self.client.get_entity(DESTINATION_GROUP_ID)
            logger.info(f"✅ Destination group: {getattr(self.destination_entity, 'title', 'Unknown')}")
        except Exception as e:
            logger.error(f"❌ Failed to get destination group: {e}")
            logger.error("Make sure DESTINATION_GROUP_ID is correct!")
            return

        logger.info(f"✅ Listening for keywords: {KEYWORDS}")
        logger.info(f"✅ Rate limit: {RATE_LIMIT} msg/sec")
        logger.info("=" * 60)

        # Register message handler
        @self.client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            await self.handle_message(event)

        # Keep running
        logger.info("👂 Listening for messages... (Press Ctrl+C to stop)")
        await self.client.run_until_disconnected()

    async def handle_message(self, event):
        """
        Handle incoming message.

        Args:
            event: Telethon NewMessage event
        """
        try:
            # Skip if not from group or channel
            if not event.is_group and not event.is_channel:
                return

            # Skip if no text
            if not event.message.text:
                return

            # Skip bot messages
            sender = event.message.sender
            if sender and getattr(sender, 'bot', False):
                return

            # Check if message matches keywords
            text = event.message.text.lower()
            matched_keywords = [kw for kw in KEYWORDS if kw.lower() in text]

            if not matched_keywords:
                return  # No match

            # Get source info
            chat = await event.get_chat()
            chat_name = getattr(chat, 'title', 'Unknown')

            logger.info(
                f"📩 Match found in '{chat_name}': "
                f"Keywords={matched_keywords} | "
                f"Text='{text[:50]}...'"
            )

            # Rate limit before forwarding
            await self.rate_limiter.acquire()

            # Forward message
            start_time = time.time()
            await self.client.forward_messages(
                self.destination_entity,
                event.message
            )
            duration = time.time() - start_time

            logger.info(
                f"✅ Forwarded in {duration:.2f}s | "
                f"From: {chat_name}"
            )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def stop(self):
        """Stop the listener."""
        if self.client:
            logger.info("🛑 Stopping listener...")
            await self.client.disconnect()
            logger.info("✅ Stopped")


async def main():
    """Main entry point."""
    listener = SimpleListener()

    try:
        await listener.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await listener.stop()


if __name__ == "__main__":
    asyncio.run(main())
