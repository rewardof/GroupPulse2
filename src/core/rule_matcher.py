"""
Rule Matching Engine

High-performance keyword and rule matching with compiled regex caching.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@dataclass
class Keyword:
    """Keyword model for matching."""
    id: int
    keyword: str
    is_regex: bool
    is_case_sensitive: bool


@dataclass
class ForwardingRule:
    """Forwarding rule model for matching."""
    id: int
    user_id: int
    source_group_ids: List[int]
    destination_group_ids: List[int]
    keyword_ids: List[int]
    require_all_keywords: bool
    exclude_keyword_ids: List[int]
    only_media: bool
    only_text: bool
    min_text_length: Optional[int]
    max_text_length: Optional[int]
    priority: int
    action: str


class RuleMatcher:
    """
    High-performance keyword and rule matching engine.

    Optimizations:
    - Compiled regex patterns (cached with LRU)
    - Early exit on mismatches
    - Efficient data structures
    """

    def __init__(self):
        self._keyword_cache: Dict[int, Keyword] = {}

    @lru_cache(maxsize=1024)
    def _compile_pattern(
        self,
        keyword: str,
        is_regex: bool,
        is_case_sensitive: bool
    ) -> re.Pattern:
        """
        Compile and cache regex pattern.

        Args:
            keyword: Keyword string
            is_regex: Whether keyword is regex
            is_case_sensitive: Whether to match case-sensitively

        Returns:
            re.Pattern: Compiled regex pattern
        """
        if is_regex:
            pattern = keyword
        else:
            # Escape special chars for literal matching
            pattern = re.escape(keyword)

        flags = 0 if is_case_sensitive else re.IGNORECASE

        try:
            return re.compile(pattern, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{keyword}': {e}")
            # Fallback to literal matching
            return re.compile(re.escape(keyword), flags)

    def match_keywords(
        self,
        text: str,
        keywords: List[Keyword],
        require_all: bool = False
    ) -> bool:
        """
        Match text against keywords.

        Args:
            text: Message text to match
            keywords: List of keyword objects
            require_all: If True, ALL keywords must match (AND logic)
                        If False, ANY keyword can match (OR logic)

        Returns:
            bool: Match result
        """
        if not keywords:
            return True  # No keywords = match all

        if not text:
            return False

        matches = []

        for kw in keywords:
            pattern = self._compile_pattern(
                kw.keyword,
                kw.is_regex,
                kw.is_case_sensitive
            )

            matched = bool(pattern.search(text))
            matches.append(matched)

            # Early exit optimization
            if require_all and not matched:
                return False  # Need all, but one failed
            if not require_all and matched:
                return True  # Need any, found one

        return all(matches) if require_all else any(matches)

    def check_rule_conditions(
        self,
        rule: ForwardingRule,
        message_data: Dict
    ) -> bool:
        """
        Check if message matches all rule conditions.

        Args:
            rule: Forwarding rule to check
            message_data: Message data dict with keys:
                - group_id: Source group ID
                - text: Message text
                - has_media: Whether message has media
                - media_type: Type of media (if any)

        Returns:
            bool: Whether rule matches
        """
        # 1. Check source group
        if message_data['group_id'] not in rule.source_group_ids:
            return False

        # 2. Check media/text filters
        has_media = message_data.get('has_media', False)
        text = message_data.get('text', '')

        if rule.only_media and not has_media:
            return False

        if rule.only_text and has_media:
            return False

        # 3. Check text length
        text_length = len(text)

        if rule.min_text_length and text_length < rule.min_text_length:
            return False

        if rule.max_text_length and text_length > rule.max_text_length:
            return False

        # 4. Check exclude keywords (blacklist)
        if rule.exclude_keyword_ids:
            exclude_keywords = [
                self._keyword_cache[kid] for kid in rule.exclude_keyword_ids
                if kid in self._keyword_cache
            ]
            if self.match_keywords(text, exclude_keywords, require_all=False):
                return False  # Matched blacklist = reject

        # 5. Check include keywords
        if rule.keyword_ids:
            include_keywords = [
                self._keyword_cache[kid] for kid in rule.keyword_ids
                if kid in self._keyword_cache
            ]
            if not self.match_keywords(text, include_keywords, rule.require_all_keywords):
                return False

        return True

    def find_matching_rules(
        self,
        message_data: Dict,
        all_rules: List[ForwardingRule]
    ) -> List[ForwardingRule]:
        """
        Find all rules that match a message.

        Rules are already sorted by priority in the input list.

        Args:
            message_data: Message data
            all_rules: List of all active rules (pre-sorted by priority)

        Returns:
            List of matching rules
        """
        matching_rules = []

        for rule in all_rules:
            if self.check_rule_conditions(rule, message_data):
                matching_rules.append(rule)

        return matching_rules

    def preload_keywords(self, keywords: List[Keyword]):
        """
        Preload keywords into cache.

        Args:
            keywords: List of keyword objects to cache
        """
        for kw in keywords:
            self._keyword_cache[kw.id] = kw
            # Pre-compile patterns
            self._compile_pattern(kw.keyword, kw.is_regex, kw.is_case_sensitive)

    def clear_cache(self):
        """Clear keyword and pattern caches."""
        self._keyword_cache.clear()
        self._compile_pattern.cache_clear()
