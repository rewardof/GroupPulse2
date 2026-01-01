"""
Bot Inline Keyboards

Keyboard builders for bot UI.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Main menu keyboard.

    Returns:
        InlineKeyboardMarkup: Main menu keyboard
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔐 Account", callback_data="menu_account"),
        InlineKeyboardButton(text="📱 Groups", callback_data="menu_groups")
    )
    builder.row(
        InlineKeyboardButton(text="🔑 Keywords", callback_data="menu_keywords"),
        InlineKeyboardButton(text="⚙️ Rules", callback_data="menu_rules")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="menu_stats"),
        InlineKeyboardButton(text="❓ Help", callback_data="menu_help")
    )

    return builder.as_markup()


def account_menu_keyboard(has_account: bool = False) -> InlineKeyboardMarkup:
    """
    Account management keyboard.

    Args:
        has_account: Whether user has account connected

    Returns:
        InlineKeyboardMarkup: Account menu keyboard
    """
    builder = InlineKeyboardBuilder()

    if has_account:
        builder.row(
            InlineKeyboardButton(text="ℹ️ Account Info", callback_data="account_info")
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Update Session", callback_data="account_update")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Disconnect", callback_data="account_disconnect")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="➕ Add Account", callback_data="account_add")
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
    )

    return builder.as_markup()


def group_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Group management keyboard.

    Returns:
        InlineKeyboardMarkup: Group menu keyboard
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Add Source", callback_data="group_add_source"),
        InlineKeyboardButton(text="➕ Add Destination", callback_data="group_add_dest")
    )
    builder.row(
        InlineKeyboardButton(text="📋 List Groups", callback_data="group_list")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Remove Group", callback_data="group_remove")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
    )

    return builder.as_markup()


def keyword_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyword management keyboard.

    Returns:
        InlineKeyboardMarkup: Keyword menu keyboard
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Add Keyword", callback_data="keyword_add")
    )
    builder.row(
        InlineKeyboardButton(text="📋 List Keywords", callback_data="keyword_list")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Remove Keyword", callback_data="keyword_remove")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
    )

    return builder.as_markup()


def rule_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Rule management keyboard.

    Returns:
        InlineKeyboardMarkup: Rule menu keyboard
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Create Rule", callback_data="rule_create")
    )
    builder.row(
        InlineKeyboardButton(text="📋 List Rules", callback_data="rule_list")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Toggle Rule", callback_data="rule_toggle"),
        InlineKeyboardButton(text="🗑 Delete Rule", callback_data="rule_delete")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
    )

    return builder.as_markup()


def confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Confirmation keyboard (Yes/No).

    Args:
        action: Action name for callback data

    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ No", callback_data=f"cancel_{action}")
    )

    return builder.as_markup()


def paginated_list_keyboard(
    items: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = 5,
    callback_prefix: str = "item"
) -> InlineKeyboardMarkup:
    """
    Paginated list keyboard.

    Args:
        items: List of items with 'id' and 'name' keys
        page: Current page (0-indexed)
        page_size: Items per page
        callback_prefix: Prefix for callback data

    Returns:
        InlineKeyboardMarkup: Paginated list keyboard
    """
    builder = InlineKeyboardBuilder()

    # Calculate pagination
    total_pages = (len(items) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(items))

    # Add item buttons
    for item in items[start_idx:end_idx]:
        builder.row(
            InlineKeyboardButton(
                text=item['name'],
                callback_data=f"{callback_prefix}_{item['id']}"
            )
        )

    # Add pagination buttons
    if total_pages > 1:
        buttons = []
        if page > 0:
            buttons.append(
                InlineKeyboardButton(text="◀️ Prev", callback_data=f"page_{page-1}")
            )
        buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="page_info")
        )
        if page < total_pages - 1:
            buttons.append(
                InlineKeyboardButton(text="Next ▶️", callback_data=f"page_{page+1}")
            )
        builder.row(*buttons)

    # Back button
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back")
    )

    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Cancel button keyboard.

    Returns:
        InlineKeyboardMarkup: Cancel keyboard
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    )
    return builder.as_markup()
