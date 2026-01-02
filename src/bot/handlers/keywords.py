"""
Keyword Management Handlers

Keywords qo'shish, ko'rish, o'chirish.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.bot.states.account_setup import KeywordSetupStates
from src.bot.keyboards.main import keyword_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.models import User, Keyword
from src.utils.validators import validate_regex_pattern
import logging

logger = logging.getLogger(__name__)

router = Router()


# =============================================================================
# Keywords Menu
# =============================================================================

@router.callback_query(F.data == "menu_keywords")
async def callback_keywords_menu(callback: CallbackQuery):
    """Keywords menu."""
    await callback.message.edit_text(
        "🔑 *Keyword Management*\n\n"
        "Keywords - messagelarni filter qilish uchun.\n\n"
        "Literal: Aniq so'z (masalan: 'bitcoin')\n"
        "Regex: Pattern (masalan: 'bitcoin|btc|crypto')\n\n"
        "Nima qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=keyword_menu_keyboard()
    )
    await callback.answer()


# =============================================================================
# Add Keyword
# =============================================================================

@router.callback_query(F.data == "keyword_add")
async def callback_add_keyword(callback: CallbackQuery, state: FSMContext):
    """Keyword qo'shishni boshlash."""
    user_id = callback.from_user.id

    # Check if user exists
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        users = await user_repo.get_multi(telegram_id=user_id, limit=1)

        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

    await callback.message.edit_text(
        "➕ *Keyword Qo'shish*\n\n"
        "Keyword yoki regex pattern yuboring.\n\n"
        "*Misollar:*\n"
        "• `bitcoin` - literal (aniq)\n"
        "• `bitcoin|btc|crypto` - regex (yoki)\n"
        "• `price.*usd` - regex pattern\n\n"
        "Keywordni yuboring:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(KeywordSetupStates.waiting_for_keyword)
    await callback.answer()


@router.message(KeywordSetupStates.waiting_for_keyword)
async def process_keyword(message: Message, state: FSMContext):
    """Keyword qabul qilish."""
    keyword_text = message.text.strip()

    if not keyword_text:
        await message.answer(
            "❌ Keyword bo'sh bo'lishi mumkin emas!\n\n"
            "Qayta yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    # Check if it's regex or literal
    # Simple heuristic: if contains |, *, +, ?, [, ], (, ), it's probably regex
    regex_chars = ['|', '*', '+', '?', '[', ']', '(', ')']
    is_regex = any(c in keyword_text for c in regex_chars)

    if is_regex:
        # Validate regex
        if not validate_regex_pattern(keyword_text):
            await message.answer(
                "❌ Regex pattern noto'g'ri!\n\n"
                "Sintaksisni tekshiring va qayta yuboring:",
                reply_markup=cancel_keyboard()
            )
            return

    await state.update_data(keyword=keyword_text, is_regex=is_regex)

    # Ask for case sensitivity
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Case Sensitive", callback_data="keyword_case_yes"),
            InlineKeyboardButton(text="❌ Case Insensitive", callback_data="keyword_case_no")
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel")]
    ])

    keyword_type = "Regex" if is_regex else "Literal"

    await message.answer(
        f"🔑 *Keyword Preview*\n\n"
        f"Text: `{keyword_text}`\n"
        f"Type: {keyword_type}\n\n"
        "Case sensitive bo'lsinmi?\n\n"
        "• Case Sensitive: Bitcoin ≠ bitcoin\n"
        "• Case Insensitive: Bitcoin = bitcoin",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("keyword_case_"))
async def callback_keyword_case(callback: CallbackQuery, state: FSMContext):
    """Case sensitivity tanlash."""
    is_case_sensitive = callback.data == "keyword_case_yes"
    data = await state.get_data()

    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        # Get user
        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        # Create keyword
        keyword = await keyword_repo.create(
            user_id=users[0].id,
            keyword=data['keyword'],
            is_regex=data['is_regex'],
            is_case_sensitive=is_case_sensitive,
            is_active=True
        )

        await session.commit()

        keyword_type = "Regex" if data['is_regex'] else "Literal"
        case_type = "Sensitive" if is_case_sensitive else "Insensitive"

        await callback.message.edit_text(
            f"✅ *Keyword qo'shildi!*\n\n"
            f"🔑 Text: `{data['keyword']}`\n"
            f"📝 Type: {keyword_type}\n"
            f"🔤 Case: {case_type}\n\n"
            f"ID: {keyword.id}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    await state.clear()
    await callback.answer()


# =============================================================================
# List Keywords
# =============================================================================

@router.callback_query(F.data == "keyword_list")
async def callback_list_keywords(callback: CallbackQuery):
    """Barcha keywords'larni ko'rsatish."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all keywords
        keywords = await keyword_repo.get_multi(user_id=users[0].id, limit=100)

        if not keywords:
            await callback.message.edit_text(
                "🔑 Hali hech qanday keyword qo'shilmagan.\n\n"
                "Keywords qo'shish uchun:\n"
                "➕ Add Keyword",
                reply_markup=keyword_menu_keyboard()
            )
            await callback.answer()
            return

        text = "🔑 *Your Keywords*\n\n"

        for kw in keywords:
            status = "🟢" if kw.is_active else "🔴"
            kw_type = "📝 Regex" if kw.is_regex else "📄 Literal"
            case = "🔤 CS" if kw.is_case_sensitive else "🔤 CI"
            matches = f"✓ {kw.match_count}" if kw.match_count > 0 else ""

            text += (
                f"{status} `{kw.keyword[:40]}`\n"
                f"   {kw_type} | {case} | ID: {kw.id} {matches}\n\n"
            )

        text += f"*Total:* {len(keywords)} keywords"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyword_menu_keyboard()
        )

    await callback.answer()


# =============================================================================
# Remove Keyword
# =============================================================================

@router.callback_query(F.data == "keyword_remove")
async def callback_remove_keyword_start(callback: CallbackQuery):
    """Keyword o'chirishni boshlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all keywords
        keywords = await keyword_repo.get_multi(user_id=users[0].id, limit=100)

        if not keywords:
            await callback.answer("Hech qanday keyword yo'q!", show_alert=True)
            return

        # Create inline keyboard with keywords
        keyboard = []
        for kw in keywords:
            kw_type = "📝" if kw.is_regex else "📄"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{kw_type} {kw.keyword[:40]}",
                    callback_data=f"remove_keyword_{kw.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_keywords")])

        await callback.message.edit_text(
            "🗑 *O'chirish uchun keyword tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("remove_keyword_"))
async def callback_remove_keyword_confirm(callback: CallbackQuery):
    """Keyword o'chirishni tasdiqlash."""
    keyword_id = int(callback.data.split("_")[2])

    async with get_async_session() as session:
        keyword_repo = BaseRepository(Keyword, session)

        keyword = await keyword_repo.get(keyword_id)
        if not keyword:
            await callback.answer("Keyword topilmadi!", show_alert=True)
            return

        # Delete keyword
        await keyword_repo.delete(keyword_id)
        await session.commit()

        await callback.message.edit_text(
            f"✅ *Keyword o'chirildi!*\n\n"
            f"🔑 `{keyword.keyword}`",
            parse_mode="Markdown",
            reply_markup=keyword_menu_keyboard()
        )

    await callback.answer()
