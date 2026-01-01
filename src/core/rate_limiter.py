"""
Rate Limiting System

Multi-layer token bucket rate limiter for Telegram API compliance.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket rate limiter.

    Algorithm:
    - Bucket has capacity and refill rate
    - Tokens added at steady rate
    - Action consumes token(s)
    - Blocks if no tokens available
    """

    capacity: int  # Max tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)

    def __post_init__(self):
        self.tokens = self.capacity  # Start full

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )

        self.last_update = now

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens (blocking if not available).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            bool: True if acquired
        """
        while True:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # Calculate wait time
            deficit = tokens - self.tokens
            wait_time = deficit / self.refill_rate

            logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens (non-blocking).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            bool: True if acquired, False if not available
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False


class RateLimiter:
    """
    Multi-layer rate limiter.

    Layers:
    1. Per-account limits (Telegram API)
    2. Per-destination limits (anti-spam)
    3. Global system limits (resource protection)
    """

    def __init__(
        self,
        global_rate: int = 100,
        account_rate: int = 20,
        destination_rate: int = 5
    ):
        """
        Initialize rate limiter.

        Args:
            global_rate: Global messages/second limit
            account_rate: Per-account messages/second limit
            destination_rate: Per-destination messages/second limit
        """
        # Per-account limiters
        self._account_limiters: Dict[int, TokenBucket] = {}

        # Per-destination limiters
        self._destination_limiters: Dict[int, TokenBucket] = {}

        # Global limiter
        self._global_limiter = TokenBucket(
            capacity=global_rate * 2,  # 2x capacity for bursts
            refill_rate=global_rate
        )

        # Configuration
        self._account_rate = account_rate
        self._destination_rate = destination_rate

        # Flood wait tracking
        self._flood_waits: Dict[int, datetime] = {}

    def _get_account_limiter(self, account_id: int) -> TokenBucket:
        """Get or create account-level rate limiter."""
        if account_id not in self._account_limiters:
            self._account_limiters[account_id] = TokenBucket(
                capacity=self._account_rate * 2,  # Allow bursts
                refill_rate=self._account_rate
            )
        return self._account_limiters[account_id]

    def _get_destination_limiter(self, destination_id: int) -> TokenBucket:
        """Get or create destination-level rate limiter."""
        if destination_id not in self._destination_limiters:
            self._destination_limiters[destination_id] = TokenBucket(
                capacity=self._destination_rate * 2,
                refill_rate=self._destination_rate
            )
        return self._destination_limiters[destination_id]

    def set_flood_wait(self, account_id: int, seconds: int):
        """
        Record flood wait for an account.

        Args:
            account_id: Account ID
            seconds: Flood wait duration in seconds
        """
        wait_until = datetime.utcnow() + timedelta(seconds=seconds)
        self._flood_waits[account_id] = wait_until
        logger.warning(f"Flood wait set for account {account_id}: {seconds}s (until {wait_until})")

    def is_flood_waited(self, account_id: int) -> bool:
        """
        Check if account is in flood wait.

        Args:
            account_id: Account ID

        Returns:
            bool: True if flood waited
        """
        if account_id in self._flood_waits:
            if datetime.utcnow() < self._flood_waits[account_id]:
                return True
            else:
                # Flood wait expired
                del self._flood_waits[account_id]
        return False

    def get_flood_wait_seconds(self, account_id: int) -> Optional[int]:
        """
        Get remaining flood wait seconds.

        Args:
            account_id: Account ID

        Returns:
            Optional[int]: Seconds remaining or None
        """
        if account_id in self._flood_waits:
            remaining = (self._flood_waits[account_id] - datetime.utcnow()).total_seconds()
            return max(0, int(remaining))
        return None

    async def acquire(
        self,
        account_id: int,
        destination_id: int,
        tokens: int = 1
    ) -> bool:
        """
        Acquire rate limit tokens across all layers.

        Args:
            account_id: Telegram account ID
            destination_id: Destination group ID
            tokens: Number of tokens (usually 1)

        Returns:
            bool: True if acquired, False if flood waited
        """
        # Check flood wait
        if self.is_flood_waited(account_id):
            remaining = self.get_flood_wait_seconds(account_id)
            logger.debug(f"Account {account_id} is flood waited ({remaining}s remaining)")
            return False

        # Acquire tokens from all layers (in order)
        await self._global_limiter.acquire(tokens)
        await self._get_account_limiter(account_id).acquire(tokens)
        await self._get_destination_limiter(destination_id).acquire(tokens)

        return True

    def try_acquire(
        self,
        account_id: int,
        destination_id: int,
        tokens: int = 1
    ) -> bool:
        """
        Try to acquire tokens (non-blocking).

        Args:
            account_id: Account ID
            destination_id: Destination ID
            tokens: Number of tokens

        Returns:
            bool: True if acquired
        """
        if self.is_flood_waited(account_id):
            return False

        # Try all layers (non-blocking)
        if not self._global_limiter.try_acquire(tokens):
            return False

        if not self._get_account_limiter(account_id).try_acquire(tokens):
            return False

        if not self._get_destination_limiter(destination_id).try_acquire(tokens):
            return False

        return True

    def clear_account_limiter(self, account_id: int):
        """Clear account rate limiter."""
        if account_id in self._account_limiters:
            del self._account_limiters[account_id]

    def clear_flood_wait(self, account_id: int):
        """Clear flood wait for account."""
        if account_id in self._flood_waits:
            del self._flood_waits[account_id]
