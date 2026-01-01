"""
Telethon Userbot Client

High-performance Telegram userbot with session string support.
"""

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from typing import List, Callable, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class GroupPulseUserbot:
    """
    High-performance Telethon userbot client.

    Features:
    - Session string based (no file I/O)
    - Automatic flood wait handling
    - Connection pooling
    - Graceful shutdown
    """

    def __init__(
        self,
        account_id: int,
        phone: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        proxy: Optional[dict] = None
    ):
        """
        Initialize userbot client.

        Args:
            account_id: Database account ID
            phone: Phone number
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_string: Session string (NOT file path)
            proxy: Optional proxy configuration
        """
        self.account_id = account_id
        self.phone = phone
        self.api_id = api_id
        self.api_hash = api_hash

        # Use StringSession (no file system dependency)
        self.client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash,
            proxy=proxy,
            connection_retries=5,
            retry_delay=1,
            timeout=10,
            request_retries=3,
            flood_sleep_threshold=0,  # Manual flood wait handling
            device_model="Desktop",
            system_version="Windows 10",
            app_version="1.0",
            lang_code="en"
        )

        self._is_running = False
        self._flood_wait_until: Optional[datetime] = None
        self._message_handlers: List[Callable] = []
        self._event_handlers: List[Any] = []

    async def start(self) -> bool:
        """
        Start the client and authenticate.

        Returns:
            bool: True if started successfully
        """
        try:
            await self.client.start(phone=self.phone)

            # Verify authorization
            if not await self.client.is_user_authorized():
                logger.error(f"Account {self.account_id} not authorized")
                return False

            self._is_running = True
            logger.info(f"✓ Userbot started for account {self.account_id} ({self.phone})")
            return True

        except FloodWaitError as e:
            self._flood_wait_until = datetime.utcnow() + timedelta(seconds=e.seconds)
            logger.warning(f"Flood wait: {e.seconds}s for account {self.account_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to start userbot {self.account_id}: {e}", exc_info=True)
            return False

    def add_message_handler(self, handler: Callable):
        """
        Register a message handler function.

        Args:
            handler: Async function to handle messages
        """
        self._message_handlers.append(handler)

    async def listen_to_groups(self, group_ids: List[int]):
        """
        Listen to specific groups for new messages.

        Optimizations:
        - Single event handler for all groups (no per-group handlers)
        - Filter by chat_id in handler (faster than multiple handlers)
        - Async processing (non-blocking)

        Args:
            group_ids: List of Telegram group IDs to monitor
        """
        if not group_ids:
            logger.warning(f"No groups to listen to for account {self.account_id}")
            return

        @self.client.on(events.NewMessage(chats=group_ids))
        async def message_handler(event):
            """Handle incoming messages."""
            # Check flood wait
            if self._flood_wait_until and datetime.utcnow() < self._flood_wait_until:
                logger.debug(f"Skipping - flood wait active until {self._flood_wait_until}")
                return

            # Extract message data
            message_data = {
                'account_id': self.account_id,
                'group_id': event.chat_id,
                'message_id': event.message.id,
                'text': event.message.text or '',
                'date': event.message.date,
                'sender_id': event.sender_id,
                'has_media': bool(event.message.media),
                'media_type': type(event.message.media).__name__ if event.message.media else None,
                'message': event.message  # Full message object for forwarding
            }

            # Process through all registered handlers (async, non-blocking)
            for handler in self._message_handlers:
                try:
                    # Fire and forget (non-blocking)
                    asyncio.create_task(handler(message_data))
                except Exception as e:
                    logger.error(f"Handler error: {e}", exc_info=True)

        # Store handler reference for cleanup
        self._event_handlers.append(message_handler)

        logger.info(f"📡 Listening to {len(group_ids)} groups on account {self.account_id}")

    async def forward_message(
        self,
        message,
        destination_chat_id: int,
        remove_caption: bool = False,
        delay_ms: int = 0
    ) -> bool:
        """
        Forward a message with flood wait handling.

        Args:
            message: Telethon message object
            destination_chat_id: Destination group ID
            remove_caption: Remove media captions
            delay_ms: Artificial delay (humanization)

        Returns:
            bool: Success status
        """
        # Check flood wait
        if self._flood_wait_until and datetime.utcnow() < self._flood_wait_until:
            wait_seconds = (self._flood_wait_until - datetime.utcnow()).total_seconds()
            logger.warning(f"Flood wait active: {wait_seconds:.1f}s remaining")
            return False

        # Humanization delay
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        try:
            # Forward message
            if remove_caption:
                # Send without caption
                await self.client.send_message(
                    destination_chat_id,
                    message.message if hasattr(message, 'message') else '',
                    file=message.media if hasattr(message, 'media') else None
                )
            else:
                # Forward with original caption
                await self.client.forward_messages(
                    destination_chat_id,
                    message
                )

            logger.debug(f"✓ Forwarded message {message.id} to {destination_chat_id}")
            return True

        except FloodWaitError as e:
            # Set flood wait timer
            self._flood_wait_until = datetime.utcnow() + timedelta(seconds=e.seconds)
            logger.warning(f"⚠️ FloodWait: {e.seconds}s for account {self.account_id}")
            return False

        except Exception as e:
            logger.error(f"Forward failed: {e}", exc_info=True)
            return False

    async def get_dialogs(self, limit: int = 100):
        """
        Get user's dialogs (chats/groups).

        Args:
            limit: Maximum number of dialogs to retrieve

        Returns:
            List of dialog objects
        """
        try:
            dialogs = await self.client.get_dialogs(limit=limit)
            return dialogs
        except Exception as e:
            logger.error(f"Failed to get dialogs: {e}")
            return []

    async def join_group(self, invite_link: str) -> bool:
        """
        Join a group via invite link.

        Args:
            invite_link: Telegram invite link

        Returns:
            bool: Success status
        """
        try:
            await self.client(functions.messages.ImportChatInviteRequest(invite_link))
            logger.info(f"Joined group via {invite_link}")
            return True
        except Exception as e:
            logger.error(f"Failed to join group: {e}")
            return False

    async def stop(self):
        """Graceful shutdown."""
        self._is_running = False

        # Remove event handlers
        for handler in self._event_handlers:
            self.client.remove_event_handler(handler)
        self._event_handlers.clear()

        # Disconnect
        if self.client.is_connected():
            await self.client.disconnect()

        logger.info(f"✓ Userbot stopped for account {self.account_id}")

    def get_session_string(self) -> str:
        """
        Get current session string for persistence.

        Returns:
            str: Session string
        """
        return self.client.session.save()

    @property
    def is_running(self) -> bool:
        """Check if userbot is running."""
        return self._is_running and self.client.is_connected()

    @property
    def is_flood_waited(self) -> bool:
        """Check if currently in flood wait."""
        if self._flood_wait_until:
            return datetime.utcnow() < self._flood_wait_until
        return False
