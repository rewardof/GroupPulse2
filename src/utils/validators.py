"""
Input Validators

Validation utilities for user input.
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number (with country code)

    Returns:
        bool: True if valid
    """
    # Remove spaces and dashes
    cleaned = phone.replace(" ", "").replace("-", "")

    # Must start with + and have 10-15 digits
    pattern = r'^\+\d{10,15}$'

    return bool(re.match(pattern, cleaned))


def validate_telegram_id(telegram_id: str) -> Optional[int]:
    """
    Validate and parse Telegram ID.

    Args:
        telegram_id: Telegram ID string

    Returns:
        Optional[int]: Parsed ID or None if invalid
    """
    try:
        # Remove common prefixes
        cleaned = telegram_id.strip()
        if cleaned.startswith('@'):
            return None  # Username, not ID

        # Parse as integer
        tid = int(cleaned)

        # Telegram IDs are positive integers
        if tid > 0:
            return tid

        return None

    except ValueError:
        return None


def validate_telegram_username(username: str) -> Optional[str]:
    """
    Validate Telegram username format.

    Args:
        username: Username (with or without @)

    Returns:
        Optional[str]: Cleaned username or None if invalid
    """
    # Remove @ if present
    cleaned = username.strip().lstrip('@')

    # Telegram usernames: 5-32 chars, alphanumeric + underscores
    pattern = r'^[a-zA-Z0-9_]{5,32}$'

    if re.match(pattern, cleaned):
        return cleaned

    return None


def validate_invite_link(link: str) -> bool:
    """
    Validate Telegram invite link format.

    Args:
        link: Invite link

    Returns:
        bool: True if valid
    """
    # Telegram invite link patterns
    patterns = [
        r'^https://t\.me/\+[a-zA-Z0-9_-]+$',
        r'^https://t\.me/joinchat/[a-zA-Z0-9_-]+$',
        r'^https://telegram\.me/\+[a-zA-Z0-9_-]+$',
        r'^https://telegram\.me/joinchat/[a-zA-Z0-9_-]+$',
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True

    return False


def validate_regex_pattern(pattern: str) -> bool:
    """
    Validate regex pattern (check if compilable).

    Args:
        pattern: Regex pattern string

    Returns:
        bool: True if valid regex
    """
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def sanitize_text(text: str, max_length: int = 4096) -> str:
    """
    Sanitize text for Telegram messages.

    Args:
        text: Input text
        max_length: Maximum length (Telegram limit is 4096)

    Returns:
        str: Sanitized text
    """
    # Remove null bytes
    sanitized = text.replace('\x00', '')

    # Trim to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."

    return sanitized


def validate_api_credentials(api_id: str, api_hash: str) -> bool:
    """
    Validate Telegram API credentials format.

    Args:
        api_id: API ID (should be numeric)
        api_hash: API hash (should be 32 hex chars)

    Returns:
        bool: True if valid format
    """
    try:
        # API ID should be integer
        int(api_id)

        # API hash should be 32 hex characters
        if len(api_hash) != 32:
            return False

        int(api_hash, 16)  # Verify it's hex

        return True

    except ValueError:
        return False
