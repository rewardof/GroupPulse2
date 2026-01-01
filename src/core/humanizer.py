"""
Human Behavior Simulator

Simulates human-like patterns to avoid detection by Telegram.
"""

import random
import asyncio
from typing import Tuple
from datetime import datetime, time as dt_time
import logging

logger = logging.getLogger(__name__)


class HumanBehaviorSimulator:
    """
    Simulate human-like patterns to avoid detection.

    Techniques:
    - Random delays between actions
    - "Active hours" simulation (less activity at night)
    - Typing simulation (delays based on message length)
    - Varied activity patterns
    - Occasional random skipping
    """

    def __init__(
        self,
        active_hours: Tuple[int, int] = (7, 23),  # 7 AM - 11 PM
        min_delay_ms: int = 100,
        max_delay_ms: int = 3000
    ):
        """
        Initialize humanizer.

        Args:
            active_hours: Tuple of (start_hour, end_hour) for active period
            min_delay_ms: Minimum delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
        """
        self.active_hours = active_hours
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms

    def is_active_hours(self) -> bool:
        """
        Check if current time is in active hours.

        Returns:
            bool: True if in active hours
        """
        now = datetime.now().time()
        start_hour = dt_time(hour=self.active_hours[0])
        end_hour = dt_time(hour=self.active_hours[1])

        return start_hour <= now <= end_hour

    def calculate_delay(self, message_length: int = 0) -> int:
        """
        Calculate human-like delay.

        Factors:
        - Random base delay
        - Message length (longer = more delay, simulating reading)
        - Time of day (slower at night)

        Args:
            message_length: Length of message text

        Returns:
            Delay in milliseconds
        """
        # Base random delay
        base_delay = random.randint(self.min_delay_ms, self.max_delay_ms)

        # Reading time (assume 300 words/min = 5 words/sec)
        if message_length > 0:
            # Average word length is 5 characters
            word_count = message_length / 5
            # 200ms per word (slower than real reading for safety)
            reading_delay_ms = int(word_count * 200)
            base_delay += min(reading_delay_ms, 5000)  # Cap at 5 seconds

        # Night time multiplier (slower activity)
        if not self.is_active_hours():
            base_delay = int(base_delay * random.uniform(1.5, 3.0))

        return base_delay

    async def sleep_random(
        self,
        min_ms: int = None,
        max_ms: int = None,
        message_length: int = 0
    ):
        """
        Sleep for a random duration.

        Args:
            min_ms: Minimum delay (overrides default)
            max_ms: Maximum delay (overrides default)
            message_length: Message length for calculation
        """
        if min_ms is not None and max_ms is not None:
            delay_ms = random.randint(min_ms, max_ms)
        else:
            delay_ms = self.calculate_delay(message_length)

        logger.debug(f"Humanizer: sleeping for {delay_ms}ms")
        await asyncio.sleep(delay_ms / 1000)

    def should_skip_action(self, probability: float = 0.05) -> bool:
        """
        Randomly skip an action (simulate human behavior).

        Args:
            probability: Chance of skipping (0.0 - 1.0)

        Returns:
            bool: True if should skip
        """
        return random.random() < probability

    def add_jitter(self, value: int, jitter_percent: int = 10) -> int:
        """
        Add random jitter to a value.

        Args:
            value: Base value
            jitter_percent: Percentage of variation (e.g., 10 = ±10%)

        Returns:
            Value with jitter applied
        """
        jitter = int(value * jitter_percent / 100)
        return value + random.randint(-jitter, jitter)

    def get_active_hours_multiplier(self) -> float:
        """
        Get activity multiplier based on time of day.

        Returns:
            float: Multiplier (1.0 = normal, <1.0 = slower)
        """
        if self.is_active_hours():
            return 1.0
        else:
            # Night time: 50-70% slower
            return random.uniform(0.3, 0.5)

    async def typing_simulation(self, text_length: int):
        """
        Simulate typing delay based on text length.

        Args:
            text_length: Length of text being typed
        """
        # Average typing speed: 40 words/min = 200 chars/min = 3.3 chars/sec
        # Add randomness
        chars_per_second = random.uniform(2.5, 4.0)
        typing_time = text_length / chars_per_second

        # Add jitter
        typing_time = self.add_jitter(int(typing_time * 1000), 20) / 1000

        logger.debug(f"Typing simulation: {typing_time:.2f}s for {text_length} chars")
        await asyncio.sleep(typing_time)
