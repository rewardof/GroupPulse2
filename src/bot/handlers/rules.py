"""
Forwarding Rules Management Handlers

Rules yaratish, ko'rish, o'chirish, toggle qilish.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.bot.states.account_setup import RuleSetupStates
from src.bot.keyboards.main import rule_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.repositories.rule_repo import RuleRepository
from src.database.models import User, Group, Keyword, ForwardingRule, GroupType, RuleAction
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
        "Rule - qaysi groupdan qaysi groupga forward qilish.\n\n"
        "Rule tarkibi:\n"
        "• Source groups (eshitish)\n"
        "• Destination groups (forward)\n"
        "• Keywords (filter)\n"
        "• Conditions (shart)\n\n"
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

    # Check if user has groups
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        # Check groups
        groups = await group_repo.get_multi(limit=100)
        source_groups = [g for g in groups if g.group_type == GroupType.SOURCE]
        dest_groups = [g for g in groups if g.group_type == GroupType.DESTINATION]

        if not source_groups:
            await callback.answer("Avval source group qo'shing!", show_alert=True)
            return

        if not dest_groups:
            await callback.answer("Avval destination group qo'shing!", show_alert=True)
            return

    await callback.message.edit_text(
        "➕ *Create Forwarding Rule*\n\n"
        "Step 1: Rule nomini kiriting\n\n"
        "Misol: 'Bitcoin News' yoki 'Crypto Signals'",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(RuleSetupStates.waiting_for_rule_name)
    await callback.answer()


@router.message(RuleSetupStates.waiting_for_rule_name)
async def process_rule_name(message: Message, state: FSMContext):
    """Rule nomini qabul qilish."""
    rule_name = message.text.strip()

    if not rule_name or len(rule_name) > 100:
        await message.answer(
            "❌ Rule nomi 1-100 belgi bo'lishi kerak!\n\n"
            "Qayta yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(rule_name=rule_name)

    # Show source groups
    user_id = message.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await message.answer("User topilmadi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        # Get source groups via account
        from src.database.repositories.account_repo import AccountRepository
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_user_id(users[0].id)

        if not account:
            await message.answer("Account topilmadi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        source_groups = await group_repo.get_multi(
            account_id=account.id,
            group_type=GroupType.SOURCE,
            limit=100
        )

        # Create keyboard
        keyboard = []
        for g in source_groups:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📥 {g.title[:40]}",
                    callback_data=f"rule_source_{g.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])

        await message.answer(
            f"✅ Rule nomi: *{rule_name}*\n\n"
            f"Step 2: Source group tanlang\n"
            f"(Qaysi groupdan eshitish?)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await state.set_state(RuleSetupStates.selecting_source_groups)


@router.callback_query(F.data.startswith("rule_source_"))
async def callback_select_source_group(callback: CallbackQuery, state: FSMContext):
    """Source group tanlash."""
    group_id = int(callback.data.split("_")[2])

    await state.update_data(source_group_ids=[group_id])

    # Show destination groups
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        from src.database.repositories.account_repo import AccountRepository
        account_repo = AccountRepository(session)
        account = await account_repo.get_by_user_id(users[0].id)

        dest_groups = await group_repo.get_multi(
            account_id=account.id,
            group_type=GroupType.DESTINATION,
            limit=100
        )

        # Create keyboard
        keyboard = []
        for g in dest_groups:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📤 {g.title[:40]}",
                    callback_data=f"rule_dest_{g.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])

        await callback.message.edit_text(
            f"Step 3: Destination group tanlang\n"
            f"(Qaysi groupga forward qilish?)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await state.set_state(RuleSetupStates.selecting_destination_groups)
    await callback.answer()


@router.callback_query(F.data.startswith("rule_dest_"))
async def callback_select_dest_group(callback: CallbackQuery, state: FSMContext):
    """Destination group tanlash."""
    group_id = int(callback.data.split("_")[2])

    await state.update_data(destination_group_ids=[group_id])

    # Ask about keywords
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, keyword qo'shish", callback_data="rule_keywords_yes")],
        [InlineKeyboardButton(text="❌ Yo'q, hammasi", callback_data="rule_keywords_no")],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        "Step 4: Keyword filter qo'shasizmi?\n\n"
        "• Ha - Faqat keyword bo'lgan messagelar\n"
        "• Yo'q - Barcha messagelar forward bo'ladi",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await callback.answer()


@router.callback_query(F.data == "rule_keywords_no")
async def callback_no_keywords(callback: CallbackQuery, state: FSMContext):
    """Keywords'siz rule yaratish."""
    await state.update_data(keyword_ids=[])
    await create_rule_final(callback, state)


@router.callback_query(F.data == "rule_keywords_yes")
async def callback_yes_keywords(callback: CallbackQuery, state: FSMContext):
    """Keywords tanlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        keywords = await keyword_repo.get_multi(user_id=users[0].id, limit=100)

        if not keywords:
            await callback.message.edit_text(
                "❌ Hech qanday keyword yo'q!\n\n"
                "Avval keywords qo'shing yoki keywords'siz davom eting.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Keywords'siz davom etish", callback_data="rule_keywords_no")],
                    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
                ])
            )
            await callback.answer()
            return

        # Create keyboard
        keyboard = []
        for kw in keywords:
            kw_type = "📝" if kw.is_regex else "📄"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{kw_type} {kw.keyword[:40]}",
                    callback_data=f"rule_keyword_{kw.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="✅ Tayyor (keywords'siz)", callback_data="rule_keywords_no")])
        keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])

        await callback.message.edit_text(
            "Step 5: Keyword tanlang\n\n"
            "(Hozircha bitta tanlaysiz, keyingi versiyada ko'p tanlab bo'ladi)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await state.set_state(RuleSetupStates.selecting_keywords)
    await callback.answer()


@router.callback_query(F.data.startswith("rule_keyword_"))
async def callback_select_keyword(callback: CallbackQuery, state: FSMContext):
    """Keyword tanlash."""
    keyword_id = int(callback.data.split("_")[2])

    await state.update_data(keyword_ids=[keyword_id])
    await create_rule_final(callback, state)


async def create_rule_final(callback: CallbackQuery, state: FSMContext):
    """Rule yaratishni tugatish."""
    data = await state.get_data()
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)
        group_repo = BaseRepository(Group, session)
        keyword_repo = BaseRepository(Keyword, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            await state.clear()
            return

        # Get group names
        source_group = await group_repo.get(data['source_group_ids'][0])
        dest_group = await group_repo.get(data['destination_group_ids'][0])

        # Get keyword names
        keyword_names = []
        for kw_id in data.get('keyword_ids', []):
            kw = await keyword_repo.get(kw_id)
            if kw:
                keyword_names.append(kw.keyword)

        # Create rule
        rule = await rule_repo.create(
            user_id=users[0].id,
            name=data['rule_name'],
            description=f"Auto-generated rule",
            source_group_ids=data['source_group_ids'],
            destination_group_ids=data['destination_group_ids'],
            keyword_ids=data.get('keyword_ids', []),
            require_all_keywords=False,
            exclude_keyword_ids=[],
            action=RuleAction.FORWARD,
            only_media=False,
            only_text=False,
            is_active=True,
            priority=0
        )

        await session.commit()

        keyword_text = ""
        if keyword_names:
            keyword_text = f"\n🔑 Keywords: {', '.join(keyword_names)}"

        await callback.message.edit_text(
            f"✅ *Rule yaratildi!*\n\n"
            f"📛 Nom: {data['rule_name']}\n"
            f"📥 Source: {source_group.title}\n"
            f"📤 Destination: {dest_group.title}"
            f"{keyword_text}\n"
            f"🆔 Rule ID: {rule.id}\n\n"
            f"Rule aktiv! Messagelar forward qilina boshlaydi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    await state.clear()
    await callback.answer("✅ Rule yaratildi!")


# =============================================================================
# List Rules
# =============================================================================

@router.callback_query(F.data == "rule_list")
async def callback_list_rules(callback: CallbackQuery):
    """Barcha rules'larni ko'rsatish."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        rule_repo = RuleRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("User topilmadi!", show_alert=True)
            return

        # Get all rules
        rules = await rule_repo.get_active_rules_by_user(users[0].id)

        if not rules:
            await callback.message.edit_text(
                "⚙️ Hali hech qanday rule yo'q.\n\n"
                "Rule yaratish uchun:\n"
                "➕ Create Rule",
                reply_markup=rule_menu_keyboard()
            )
            await callback.answer()
            return

        text = "⚙️ *Your Forwarding Rules*\n\n"

        for rule in rules:
            status = "🟢" if rule.is_active else "🔴"
            stats = f"✓{rule.total_forwarded}" if rule.total_forwarded > 0 else ""

            text += (
                f"{status} *{rule.name}*\n"
                f"   ID: {rule.id} | Priority: {rule.priority} {stats}\n"
                f"   Sources: {len(rule.source_group_ids)} | Dests: {len(rule.destination_group_ids)}\n"
                f"   Keywords: {len(rule.keyword_ids)}\n\n"
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
                    text=f"{status} {rule.name[:40]}",
                    callback_data=f"toggle_rule_{rule.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_rules")])

        await callback.message.edit_text(
            "🔄 *Toggle Rule (On/Off)*\n\n"
            "Rule tanlang:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("toggle_rule_"))
async def callback_toggle_rule_confirm(callback: CallbackQuery):
    """Rule toggle qilish."""
    rule_id = int(callback.data.split("_")[2])

    async with get_async_session() as session:
        rule_repo = RuleRepository(session)

        rule = await rule_repo.toggle_rule(rule_id)
        await session.commit()

        if not rule:
            await callback.answer("Rule topilmadi!", show_alert=True)
            return

        status = "🟢 Active" if rule.is_active else "🔴 Inactive"

        await callback.message.edit_text(
            f"✅ *Rule o'zgartirildi!*\n\n"
            f"📛 {rule.name}\n"
            f"📊 Status: {status}",
            parse_mode="Markdown",
            reply_markup=rule_menu_keyboard()
        )

    await callback.answer(f"Status: {'Active' if rule.is_active else 'Inactive'}")


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

        # Create keyboard
        keyboard = []
        for rule in rules:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑 {rule.name[:40]}",
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
        rule_repo = RuleRepository(session)

        rule = await rule_repo.get(rule_id)
        if not rule:
            await callback.answer("Rule topilmadi!", show_alert=True)
            return

        # Delete rule
        await rule_repo.delete(rule_id)
        await session.commit()

        await callback.message.edit_text(
            f"✅ *Rule o'chirildi!*\n\n"
            f"📛 {rule.name}",
            parse_mode="Markdown",
            reply_markup=rule_menu_keyboard()
        )

    await callback.answer()
