"""
Forwarding Rules Management Handlers

Rules yaratish, ko'rish, o'chirish, toggle qilish.
Barcha source grouplardan listen qiladi, destination groupga forward qiladi.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.bot.states.account_setup import RuleSetupStates
from src.bot.keyboards.main import rule_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.repositories.account_repo import AccountRepository
from src.database.repositories.rule_repo import RuleRepository
from src.database.models import User, Group, Keyword, ForwardingRule, RuleAction
import logging

logger = logging.getLogger(__name__)

router = Router()


# =============================================================================
# Rules Menu
# =============================================================================

@router.callback_query(F.data == "menu_rules")
async def callback_rules_menu(callback: CallbackQuery):
    """Rules menu."""
    await callback.message.edit_text(
        "⚙️ *Forwarding Rules*\n\n"
        "Rule - Keywordlarga mos messagelarni forward qilish.\n\n"
        "🤖 Bot accountingizdagi *barcha* grouplardan listen qiladi.\n"
        "📨 Keywordlarga mos kelgan messagelar destination groupga forward qilinadi.\n\n"
        "Nima qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=rule_menu_keyboard()
    )
    await callback.answer()


# =============================================================================
# Create Rule
# =============================================================================

@router.callback_query(F.data == "rule_create")
async def callback_create_rule(callback: CallbackQuery, state: FSMContext):
    """Rule yaratishni boshlash."""
    user_id = callback.from_user.id

    # Check prerequisites
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        # Check if has destination group
        destination_group = await group_repo.get_multi(account_id=account.id, limit=1)
        if not destination_group:
            await callback.answer(
                "Avval destination group qo'shing!\n\n"
                "Groups → Add Destination",
                show_alert=True
            )
            return

    await callback.message.edit_text(
        "➕ *Rule Yaratish*\n\n"
        "Rule uchun nom yuboring:\n\n"
        "Masalan: `Bitcoin News`, `Crypto Alerts`, va h.k.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(RuleSetupStates.waiting_for_rule_name)
    await callback.answer()


@router.message(RuleSetupStates.waiting_for_rule_name)
async def process_rule_name(message: Message, state: FSMContext):
    """Rule nomini qabul qilish."""
    rule_name = message.text.strip()

    if not rule_name:
        await message.answer(
            "❌ Rule nomi bo'sh bo'lishi mumkin emas!\n\n"
            "Qayta yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    if len(rule_name) > 128:
        await message.answer(
            "❌ Rule nomi juda uzun (max 128 belgi)!\n\n"
            "Qisqaroq nom yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(rule_name=rule_name)

    # Ask for keywords
    user_id = message.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await message.answer("User topilmadi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        # Get all keywords
        keywords = await keyword_repo.get_multi(user_id=users[0].id, limit=100)

        if not keywords:
            # No keywords - create rule without keywords (forward everything)
            await message.answer(
                f"⚠️ Sizda hali keyword yo'q.\n\n"
                f"Rule *barcha* messagelarni forward qiladi.\n\n"
                f"Keyword qo'shish uchun:\n"
                f"Keywords → Add Keyword\n\n"
                f"Davom etamizmi?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Ha, yaratish", callback_data="create_rule_no_keywords"),
                        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
                    ]
                ])
            )
            return

        # Has keywords - let user select
        keyboard = []
        for kw in keywords:
            kw_type = "📝" if kw.is_regex else "📄"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{kw_type} {kw.keyword[:40]}",
                    callback_data=f"toggle_keyword_{kw.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="✅ Keywordlarsiz davom etish", callback_data="create_rule_no_keywords")])
        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel")])

        await state.update_data(selected_keywords=[])

        await message.answer(
            f"🔑 *Keywordlarni tanlang*\n\n"
            f"Rule nomi: `{rule_name}`\n\n"
            f"Keywordlarni tanlang (bir nechta mumkin):\n"
            f"Tanlangan: 0\n\n"
            f"Yoki keywordlarsiz davom eting (barcha messagelar).",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("toggle_keyword_"))
async def callback_toggle_keyword(callback: CallbackQuery, state: FSMContext):
    """Keyword tanlash/bekor qilish."""
    keyword_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get('selected_keywords', [])

    if keyword_id in selected:
        selected.remove(keyword_id)
    else:
        selected.append(keyword_id)

    await state.update_data(selected_keywords=selected)

    # Update keyboard
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        keywords = await keyword_repo.get_multi(user_id=users[0].id, limit=100)

        keyboard = []
        for kw in keywords:
            kw_type = "📝" if kw.is_regex else "📄"
            is_selected = "✅ " if kw.id in selected else ""
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{is_selected}{kw_type} {kw.keyword[:40]}",
                    callback_data=f"toggle_keyword_{kw.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="✅ Tayyor (Davom etish)", callback_data="create_rule_with_keywords")])
        keyboard.append([InlineKeyboardButton(text="❌ Keywordlarsiz", callback_data="create_rule_no_keywords")])
        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel")])

        await callback.message.edit_text(
            f"🔑 *Keywordlarni tanlang*\n\n"
            f"Rule nomi: `{data['rule_name']}`\n\n"
            f"Tanlangan: {len(selected)} ta keyword\n\n"
            f"Keywordlarni tanlang (bir nechta mumkin):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data == "create_rule_with_keywords")
async def callback_create_rule_with_keywords(callback: CallbackQuery, state: FSMContext):
    """Keywordlar bilan rule yaratish."""
    user_id = callback.from_user.id
    data = await state.get_data()

    selected_keywords = data.get('selected_keywords', [])

    if not selected_keywords:
        await callback.answer("Hech qanday keyword tanlanmagan!", show_alert=True)
        return

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        # Create rule
        rule = await rule_repo.create(
            user_id=users[0].id,
            name=data['rule_name'],
            keyword_ids=selected_keywords,
            action=RuleAction.FORWARD,
            is_active=True
        )

        await session.commit()

        await callback.message.edit_text(
            f"✅ *Rule yaratildi!*\n\n"
            f"📝 Nom: {data['rule_name']}\n"
            f"🔑 Keywords: {len(selected_keywords)} ta\n"
            f"🟢 Status: Active\n\n"
            f"🤖 Bot accountingizdagi *barcha* grouplardan listen qiladi.\n"
            f"📨 Keywordlarga mos messagelar destination groupga forward qilinadi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "create_rule_no_keywords")
async def callback_create_rule_no_keywords(callback: CallbackQuery, state: FSMContext):
    """Keywordlarsiz rule yaratish."""
    user_id = callback.from_user.id
    data = await state.get_data()

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        # Create rule without keywords
        rule = await rule_repo.create(
            user_id=users[0].id,
            name=data['rule_name'],
            keyword_ids=[],
            action=RuleAction.FORWARD,
            is_active=True
        )

        await session.commit()

        await callback.message.edit_text(
            f"✅ *Rule yaratildi!*\n\n"
            f"📝 Nom: {data['rule_name']}\n"
            f"🔑 Keywords: Yo'q (barcha messagelar)\n"
            f"🟢 Status: Active\n\n"
            f"⚠️ Bu rule *barcha* messagelarni forward qiladi!\n\n"
            f"🤖 Bot accountingizdagi *barcha* grouplardan listen qiladi.\n"
            f"📨 Barcha messagelar destination groupga forward qilinadi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    await state.clear()
    await callback.answer()


# =============================================================================
# List Rules
# =============================================================================

@router.callback_query(F.data == "rule_list")
async def callback_list_rules(callback: CallbackQuery):
    """Barcha rulelarni ko'rsatish."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all rules
        rules = await rule_repo.get_multi(user_id=users[0].id, limit=100)

        if not rules:
            await callback.message.edit_text(
                "⚙️ Hali hech qanday rule yaratilmagan.\n\n"
                "Rule yaratish uchun:\n"
                "➕ Create Rule",
                reply_markup=rule_menu_keyboard()
            )
            await callback.answer()
            return

        text = "⚙️ *Your Rules*\n\n"

        for rule in rules:
            status = "🟢" if rule.is_active else "🔴"
            keyword_count = len(rule.keyword_ids) if rule.keyword_ids else 0

            text += (
                f"{status} *{rule.name}*\n"
                f"   🔑 Keywords: {keyword_count}\n"
                f"   📨 Forwarded: {rule.total_forwarded}\n"
                f"   ID: {rule.id}\n\n"
            )

        text += f"*Total:* {len(rules)} rules"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=rule_menu_keyboard()
        )

    await callback.answer()


# =============================================================================
# Toggle Rule
# =============================================================================

@router.callback_query(F.data == "rule_toggle")
async def callback_toggle_rule_start(callback: CallbackQuery):
    """Rule toggle qilishni boshlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all rules
        rules = await rule_repo.get_multi(user_id=users[0].id, limit=100)

        if not rules:
            await callback.answer("Hech qanday rule yo'q!", show_alert=True)
            return

        # Create inline keyboard
        keyboard = []
        for rule in rules:
            status = "🟢" if rule.is_active else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {rule.name}",
                    callback_data=f"do_toggle_rule_{rule.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_rules")])

        await callback.message.edit_text(
            "🔄 *Toggle Rule*\n\n"
            "Rule tanlang (on/off):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("do_toggle_rule_"))
async def callback_do_toggle_rule(callback: CallbackQuery):
    """Rule ni toggle qilish."""
    rule_id = int(callback.data.split("_")[3])

    async with get_async_session() as session:
        rule_repo = BaseRepository(ForwardingRule, session)

        rule = await rule_repo.get(rule_id)
        if not rule:
            await callback.answer("Rule topilmadi!", show_alert=True)
            return

        # Toggle
        rule.is_active = not rule.is_active
        await session.commit()

        status = "🟢 Active" if rule.is_active else "🔴 Inactive"

        await callback.message.edit_text(
            f"✅ *Rule toggled!*\n\n"
            f"📝 {rule.name}\n"
            f"Status: {status}",
            parse_mode="Markdown",
            reply_markup=rule_menu_keyboard()
        )

    await callback.answer()


# =============================================================================
# Delete Rule
# =============================================================================

@router.callback_query(F.data == "rule_delete")
async def callback_delete_rule_start(callback: CallbackQuery):
    """Rule o'chirishni boshlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all rules
        rules = await rule_repo.get_multi(user_id=users[0].id, limit=100)

        if not rules:
            await callback.answer("Hech qanday rule yo'q!", show_alert=True)
            return

        # Create inline keyboard
        keyboard = []
        for rule in rules:
            status = "🟢" if rule.is_active else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {rule.name}",
                    callback_data=f"delete_rule_{rule.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_rules")])

        await callback.message.edit_text(
            "🗑 *O'chirish uchun rule tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("delete_rule_"))
async def callback_delete_rule_confirm(callback: CallbackQuery):
    """Rule o'chirishni tasdiqlash."""
    rule_id = int(callback.data.split("_")[2])

    async with get_async_session() as session:
        rule_repo = BaseRepository(ForwardingRule, session)

        rule = await rule_repo.get(rule_id)
        if not rule:
            await callback.answer("Rule topilmadi!", show_alert=True)
            return

        # Delete rule
        await rule_repo.delete(rule_id)
        await session.commit()

        await callback.message.edit_text(
            f"✅ *Rule o'chirildi!*\n\n"
            f"📝 {rule.name}",
            parse_mode="Markdown",
            reply_markup=rule_menu_keyboard()
        )

    await callback.answer()
