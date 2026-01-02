"""
Userbot Manager

Manages all userbot instances, monitors accounts, and handles message forwarding.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple, List
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
        self.rule_matchers: Dict[int, Tuple] = {}  # user_id -> (RuleMatcher, keywords_list)
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
            rule_matcher, keywords = await self._create_rule_matcher(user.id)

            # Store
            self.clients[account.id] = client
            self.destination_groups[account.id] = destination_group.telegram_id
            self.rule_matchers[user.id] = (rule_matcher, keywords)

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

    async def _create_rule_matcher(self, user_id: int) -> Tuple[RuleMatcher, List]:
        """
        Create rule matcher for user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (RuleMatcher instance, list of Keyword objects for matching)
        """
        try:
            async with get_async_session() as session:
                keyword_repo = BaseRepository(Keyword, session)
                rule_repo = BaseRepository(ForwardingRule, session)

                # Get active rules
                rules = await rule_repo.get_multi(user_id=user_id, is_active=True, limit=100)

                # Get all keywords
                db_keywords = await keyword_repo.get_multi(user_id=user_id, limit=1000)

                # Collect all keyword IDs from active rules
                keyword_ids_in_rules = set()
                for rule in rules:
                    if rule.keyword_ids:
                        keyword_ids_in_rules.update(rule.keyword_ids)

                # Convert to RuleMatcher Keyword objects
                from src.core.rule_matcher import Keyword as MatcherKeyword

                matcher_keywords = []
                for db_kw in db_keywords:
                    if db_kw.id in keyword_ids_in_rules or not keyword_ids_in_rules:
                        matcher_keywords.append(
                            MatcherKeyword(
                                id=db_kw.id,
                                keyword=db_kw.keyword,
                                is_regex=db_kw.is_regex,
                                is_case_sensitive=db_kw.is_case_sensitive
                            )
                        )

                # Create matcher and preload keywords
                rule_matcher = RuleMatcher()
                rule_matcher.preload_keywords(matcher_keywords)

                return rule_matcher, matcher_keywords

        except Exception as e:
            logger.error(f"Error creating rule matcher for user {user_id}: {e}", exc_info=True)
            return RuleMatcher(), []

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

            # Get rule matcher and keywords
            matcher_data = self.rule_matchers.get(user_id)
            if not matcher_data:
                return

            rule_matcher, keywords = matcher_data

            # If no keywords, forward everything (rule without keywords)
            if not keywords:
                # No keywords = forward all messages
                pass  # Continue to forwarding
            else:
                # Check if message matches any keywords
                if not rule_matcher.match_keywords(message.text, keywords, require_all=False):
                    return  # No match, skip

            # Get destination group
            destination_telegram_id = self.destination_groups.get(account_id)
            if not destination_telegram_id:
                logger.warning(f"No destination group for account {account_id}")
                return

            # Get client
            client = self.clients.get(account_id)
            if not client:
                return

            # Send message (copy instead of forward)
            try:
                # Get source chat info
                source_chat = await event.get_chat()
                source_title = getattr(source_chat, 'title', 'Unknown')

                # Get sender info
                sender = await event.get_sender()
                sender_username = getattr(sender, 'username', None)
                sender_name = None

                if sender_username:
                    sender_display = f"@{sender_username}"
                else:
                    # Use first name or "Unknown"
                    first_name = getattr(sender, 'first_name', None)
                    last_name = getattr(sender, 'last_name', None)
                    if first_name:
                        sender_name = first_name
                        if last_name:
                            sender_name += f" {last_name}"
                        sender_display = sender_name
                    else:
                        sender_display = "Noma'lum foydalanuvchi"

                # Get message link
                message_link = None
                if hasattr(source_chat, 'username') and source_chat.username:
                    # Public group - create link
                    message_link = f"https://t.me/{source_chat.username}/{message.id}"
                else:
                    # Private group - can't create link
                    message_link = None

                # Format new message
                formatted_text = "❗️ Yangi e'lon topildi!\n\n"
                formatted_text += f"👤 Foydalanuvchi: {sender_display}\n"

                if message_link:
                    formatted_text += f"📍 Guruhdan: [{source_title}]({message_link})\n\n"
                else:
                    formatted_text += f"📍 Guruhdan: {source_title}\n\n"

                formatted_text += f"Original xabar:\n{message.text}"

                # Get destination entity
                try:
                    destination_entity = await client.get_entity(destination_telegram_id)
                except Exception as e:
                    logger.error(f"Failed to get destination entity: {e}")
                    # Try using the ID directly
                    destination_entity = destination_telegram_id

                # Send message
                await client.send_message(
                    destination_entity,
                    formatted_text,
                    parse_mode='markdown'
                )

                logger.info(
                    f"✅ Sent: '{message.text[:50]}...' "
                    f"from {source_title} to destination"
                )

                # TODO: Update statistics in database

            except Exception as e:
                logger.error(f"Error sending message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def reload_rules(self, user_id: int):
        """
        Reload rules and keywords for a user.

        Args:
            user_id: User ID
        """
        try:
            rule_matcher, keywords = await self._create_rule_matcher(user_id)
            self.rule_matchers[user_id] = (rule_matcher, keywords)
            logger.info(f"✓ Reloaded rules for user {user_id}")
        except Exception as e:
            logger.error(f"Error reloading rules for user {user_id}: {e}", exc_info=True)
