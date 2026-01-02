"""
Userbot Manager

Manages all userbot instances, monitors accounts, and handles message forwarding.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Message

from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.repositories.account_repo import AccountRepository
from src.database.models import TelegramAccount, User, Group, Keyword, ForwardingRule
from src.core.rule_matcher import RuleMatcher
from config.settings import settings

logger = logging.getLogger(__name__)


class UserbotManager:
    """
    Manages all userbot instances.

    - Monitors active accounts from database
    - Creates Telethon client for each account
    - Listens to ALL groups in account
    - Forwards matching messages to destination group
    """

    def __init__(self):
        """Initialize userbot manager."""
        self.clients: Dict[int, TelegramClient] = {}  # account_id -> client
        self.destination_groups: Dict[int, int] = {}  # account_id -> destination_group_telegram_id
        self.rule_matchers: Dict[int, RuleMatcher] = {}  # user_id -> RuleMatcher
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start monitoring accounts and handling messages."""
        self._running = True
        logger.info("🤖 Userbot Manager starting...")

        # Initial load of accounts
        await self._load_accounts()

        # Start periodic account monitor
        self._monitor_task = asyncio.create_task(self._monitor_accounts())

        logger.info(f"✅ Userbot Manager started ({len(self.clients)} accounts)")

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        """Stop all userbots gracefully."""
        self._running = False
        logger.info("🛑 Stopping Userbot Manager...")

        # Cancel monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Disconnect all clients
        for account_id, client in list(self.clients.items()):
            try:
                await client.disconnect()
                logger.info(f"  ✓ Disconnected account {account_id}")
            except Exception as e:
                logger.error(f"  ✗ Error disconnecting account {account_id}: {e}")

        self.clients.clear()
        self.destination_groups.clear()
        self.rule_matchers.clear()

        logger.info("✅ Userbot Manager stopped")

    async def _monitor_accounts(self):
        """Periodically check for new/updated accounts."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._load_accounts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in account monitor: {e}", exc_info=True)

    async def _load_accounts(self):
        """Load active accounts from database and start clients."""
        try:
            async with get_async_session() as session:
                account_repo = AccountRepository(session)
                user_repo = BaseRepository(User, session)
                group_repo = BaseRepository(Group, session)

                # Get all active accounts
                accounts = await account_repo.get_multi(is_active=True, is_authorized=True, limit=100)

                for account in accounts:
                    # Skip if already running
                    if account.id in self.clients:
                        continue

                    # Get user
                    user = await user_repo.get(account.user_id)
                    if not user:
                        logger.warning(f"User not found for account {account.id}")
                        continue

                    # Get destination group
                    dest_groups = await group_repo.get_multi(account_id=account.id, limit=1)
                    if not dest_groups:
                        logger.info(f"No destination group for account {account.id}, skipping")
                        continue

                    destination_group = dest_groups[0]

                    # Start userbot for this account
                    await self._start_userbot(account, user, destination_group)

        except Exception as e:
            logger.error(f"Error loading accounts: {e}", exc_info=True)

    async def _start_userbot(self, account: TelegramAccount, user: User, destination_group: Group):
        """
        Start userbot for an account.

        Args:
            account: TelegramAccount instance
            user: User instance
            destination_group: Destination group
        """
        try:
            logger.info(f"🚀 Starting userbot for account {account.id} ({account.phone_number})")

            # Create Telethon client
            client = TelegramClient(
                StringSession(account.session_string),
                account.api_id,
                account.api_hash,
                device_model=f"GroupPulse-{settings.APP_VERSION}",
                system_version="Ubuntu 22.04",
                app_version=settings.APP_VERSION,
            )

            await client.connect()

            if not await client.is_user_authorized():
                logger.error(f"Account {account.id} not authorized!")
                return

            # Get user's rules and keywords
            rule_matcher = await self._create_rule_matcher(user.id)

            # Store
            self.clients[account.id] = client
            self.destination_groups[account.id] = destination_group.telegram_id
            self.rule_matchers[user.id] = rule_matcher

            # Register message handler - listens to ALL groups
            @client.on(events.NewMessage())
            async def message_handler(event):
                await self._handle_message(event, account.id, user.id)

            # Get account info
            me = await client.get_me()
            logger.info(f"  ✓ Connected: {me.first_name} (@{me.username})")
            logger.info(f"  ✓ Listening to ALL groups")
            logger.info(f"  ✓ Forwarding to: {destination_group.title}")

        except Exception as e:
            logger.error(f"Failed to start userbot for account {account.id}: {e}", exc_info=True)

    async def _create_rule_matcher(self, user_id: int) -> RuleMatcher:
        """
        Create rule matcher for user.

        Args:
            user_id: User ID

        Returns:
            RuleMatcher instance
        """
        try:
            async with get_async_session() as session:
                keyword_repo = BaseRepository(Keyword, session)
                rule_repo = BaseRepository(ForwardingRule, session)

                # Get active rules
                rules = await rule_repo.get_multi(user_id=user_id, is_active=True, limit=100)

                # Get keywords
                keywords = await keyword_repo.get_multi(user_id=user_id, limit=1000)

                # Create matcher
                rule_matcher = RuleMatcher()

                for rule in rules:
                    # Get keywords for this rule
                    rule_keywords = [kw for kw in keywords if kw.id in rule.keyword_ids]

                    # Add to matcher
                    # Note: We don't have source_group_ids anymore, so all rules apply to all groups
                    for keyword in rule_keywords:
                        rule_matcher.add_pattern(
                            keyword.keyword,
                            is_regex=keyword.is_regex,
                            is_case_sensitive=keyword.is_case_sensitive
                        )

                return rule_matcher

        except Exception as e:
            logger.error(f"Error creating rule matcher for user {user_id}: {e}", exc_info=True)
            return RuleMatcher()

    async def _handle_message(self, event: events.NewMessage.Event, account_id: int, user_id: int):
        """
        Handle incoming message.

        Args:
            event: Telethon message event
            account_id: Account ID
            user_id: User ID
        """
        try:
            message: Message = event.message

            # Skip if no text
            if not message.text:
                return

            # Get rule matcher
            rule_matcher = self.rule_matchers.get(user_id)
            if not rule_matcher:
                return

            # Check if message matches any keywords
            if not rule_matcher.match_message(message.text):
                return

            # Get destination group
            destination_telegram_id = self.destination_groups.get(account_id)
            if not destination_telegram_id:
                logger.warning(f"No destination group for account {account_id}")
                return

            # Get client
            client = self.clients.get(account_id)
            if not client:
                return

            # Forward message
            try:
                # Get source chat info
                source_chat = await event.get_chat()
                source_title = getattr(source_chat, 'title', 'Unknown')

                # Forward message
                await client.forward_messages(
                    destination_telegram_id,
                    message
                )

                logger.info(
                    f"✅ Forwarded: '{message.text[:50]}...' "
                    f"from {source_title} to destination"
                )

                # TODO: Update statistics in database

            except Exception as e:
                logger.error(f"Error forwarding message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def reload_rules(self, user_id: int):
        """
        Reload rules and keywords for a user.

        Args:
            user_id: User ID
        """
        try:
            rule_matcher = await self._create_rule_matcher(user_id)
            self.rule_matchers[user_id] = rule_matcher
            logger.info(f"✓ Reloaded rules for user {user_id}")
        except Exception as e:
            logger.error(f"Error reloading rules for user {user_id}: {e}", exc_info=True)
