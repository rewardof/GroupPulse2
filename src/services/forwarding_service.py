"""
Message Forwarding Service

Central orchestration of message processing, rule matching, and forwarding.
"""

from typing import Dict, Optional, List
from datetime import datetime
from src.core.rule_matcher import RuleMatcher, Keyword, ForwardingRule as RuleMatcherRule
from src.core.rate_limiter import RateLimiter
from src.userbot.worker import UserbotWorkerPool
from src.database.models import ForwardingRule, Keyword as KeywordModel
import hashlib
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class ForwardingService:
    """
    Central service for message forwarding orchestration.

    Responsibilities:
    - Rule matching
    - Rate limiting
    - Deduplication
    - Forwarding execution
    - Statistics tracking
    """

    def __init__(
        self,
        rule_matcher: RuleMatcher,
        rate_limiter: RateLimiter,
        userbot_pool: UserbotWorkerPool
    ):
        """
        Initialize forwarding service.

        Args:
            rule_matcher: Rule matching engine
            rate_limiter: Rate limiting system
            userbot_pool: Userbot worker pool
        """
        self.rule_matcher = rule_matcher
        self.rate_limiter = rate_limiter
        self.userbot_pool = userbot_pool

        # In-memory deduplication cache (last 1 hour)
        self._seen_messages: Dict[str, datetime] = {}

        # Statistics
        self._stats = {
            'total_processed': 0,
            'total_forwarded': 0,
            'total_skipped': 0,
            'total_duplicates': 0,
            'total_rate_limited': 0
        }

    def _calculate_message_hash(self, message_data: Dict) -> str:
        """
        Calculate SHA-256 hash of message content.

        Args:
            message_data: Message data dict

        Returns:
            str: SHA-256 hash (hex)
        """
        content = f"{message_data['account_id']}:{message_data['group_id']}:{message_data['text']}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _is_duplicate(self, message_hash: str) -> bool:
        """
        Check if message was seen recently (1 hour window).

        Args:
            message_hash: Message hash

        Returns:
            bool: True if duplicate
        """
        if message_hash in self._seen_messages:
            seen_at = self._seen_messages[message_hash]
            age_seconds = (datetime.utcnow() - seen_at).total_seconds()

            if age_seconds < 3600:  # 1 hour
                return True
            else:
                # Expired, remove from cache
                del self._seen_messages[message_hash]

        return False

    def _cleanup_dedup_cache(self):
        """Cleanup old entries from deduplication cache."""
        now = datetime.utcnow()
        expired = []

        for msg_hash, seen_at in self._seen_messages.items():
            age_seconds = (now - seen_at).total_seconds()
            if age_seconds > 3600:  # 1 hour
                expired.append(msg_hash)

        for msg_hash in expired:
            del self._seen_messages[msg_hash]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired dedup entries")

    async def process_message(
        self,
        message_data: Dict,
        user_rules: List[ForwardingRule],
        keywords: List[KeywordModel]
    ):
        """
        Process incoming message through forwarding pipeline.

        Pipeline:
        1. Deduplication check
        2. Rule matching
        3. Rate limiting
        4. Forwarding
        5. Statistics update

        Args:
            message_data: Message data from userbot
            user_rules: User's active forwarding rules
            keywords: User's keywords for matching
        """
        start_time = time.time()
        self._stats['total_processed'] += 1

        # 1. Deduplication
        message_hash = self._calculate_message_hash(message_data)

        if self._is_duplicate(message_hash):
            logger.debug(f"Duplicate message: {message_hash[:8]}...")
            self._stats['total_duplicates'] += 1
            return

        self._seen_messages[message_hash] = datetime.utcnow()

        # Periodic cache cleanup (every 1000 messages)
        if self._stats['total_processed'] % 1000 == 0:
            self._cleanup_dedup_cache()

        # 2. Preload keywords into matcher cache
        keyword_objects = [
            Keyword(
                id=kw.id,
                keyword=kw.keyword,
                is_regex=kw.is_regex,
                is_case_sensitive=kw.is_case_sensitive
            )
            for kw in keywords
        ]
        self.rule_matcher.preload_keywords(keyword_objects)

        # 3. Convert database rules to matcher rules
        matcher_rules = [
            RuleMatcherRule(
                id=rule.id,
                user_id=rule.user_id,
                source_group_ids=rule.source_group_ids,
                destination_group_ids=rule.destination_group_ids,
                keyword_ids=rule.keyword_ids,
                require_all_keywords=rule.require_all_keywords,
                exclude_keyword_ids=rule.exclude_keyword_ids,
                only_media=rule.only_media,
                only_text=rule.only_text,
                min_text_length=rule.min_text_length,
                max_text_length=rule.max_text_length,
                priority=rule.priority,
                action=rule.action.value
            )
            for rule in user_rules
        ]

        # 4. Find matching rules
        matching_rules = self.rule_matcher.find_matching_rules(message_data, matcher_rules)

        if not matching_rules:
            logger.debug(f"No matching rules for message from group {message_data['group_id']}")
            self._stats['total_skipped'] += 1
            return

        logger.info(f"📨 Message matched {len(matching_rules)} rule(s)")

        # 5. Forward to destinations
        account_id = message_data['account_id']
        forwarded_count = 0
        skipped_count = 0

        for rule in matching_rules:
            for dest_id in rule.destination_group_ids:
                # Rate limiting check
                can_send = await self.rate_limiter.acquire(account_id, dest_id)

                if not can_send:
                    logger.warning(f"⚠️ Rate limit: {account_id} -> {dest_id}")
                    self._stats['total_rate_limited'] += 1
                    skipped_count += 1
                    continue

                # Get userbot worker
                userbot = self.userbot_pool.workers.get(account_id)
                if not userbot:
                    logger.error(f"Userbot not found: {account_id}")
                    skipped_count += 1
                    continue

                # Determine action
                remove_caption = (rule.action == 'forward_no_caption')

                # Forward message
                success = await userbot.forward_message(
                    message_data['message'],
                    dest_id,
                    remove_caption=remove_caption,
                    delay_ms=0  # Delay handled by humanizer in rule
                )

                if success:
                    forwarded_count += 1
                    logger.info(f"✓ Forwarded: {account_id} -> {dest_id}")
                else:
                    skipped_count += 1

        # 6. Update statistics
        self._stats['total_forwarded'] += forwarded_count
        self._stats['total_skipped'] += skipped_count

        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"Processing complete: {forwarded_count} forwarded, "
            f"{skipped_count} skipped, {processing_time_ms}ms"
        )

    def get_stats(self) -> Dict:
        """
        Get forwarding statistics.

        Returns:
            Dict: Statistics
        """
        return self._stats.copy()

    def reset_stats(self):
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0
        logger.info("Statistics reset")
