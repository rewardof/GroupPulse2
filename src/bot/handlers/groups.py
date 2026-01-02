"""
Group Management Handlers

Source va destination groups qo'shish, ko'rish, o'chirish.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.bot.states.account_setup import GroupSetupStates
from src.bot.keyboards.main import group_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.repositories.account_repo import AccountRepository
from src.database.models import User, TelegramAccount, Group, GroupType
from src.utils.validators import validate_telegram_id, validate_telegram_username
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
import logging

logger = logging.getLogger(__name__)

router = Router()


# =============================================================================
# Groups Menu
# =============================================================================

@router.callback_query(F.data == "menu_groups")
async def callback_groups_menu(callback: CallbackQuery):
    """Groups menu."""
    await callback.message.edit_text(
        "📱 *Group Management*\n\n"
        "Source Groups: Eshitish uchun\n"
        "Destination Groups: Forward qilish uchun\n\n"
        "Nima qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=group_menu_keyboard()
    )
    await callback.answer()


# =============================================================================
# Add Source Group
# =============================================================================

@router.callback_query(F.data == "group_add_source")
async def callback_add_source_group(callback: CallbackQuery, state: FSMContext):
    """Source group qo'shishni boshlash."""
    user_id = callback.from_user.id

    # Check if user has account
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

    await state.update_data(group_type="source")

    await callback.message.edit_text(
        "➕ *Source Group Qo'shish*\n\n"
        "Source group - siz eshitmoqchi bo'lgan group.\n\n"
        "Group ID yoki username yuboring:\n"
        "• Username: @groupname\n"
        "• ID: -1001234567890\n\n"
        "Yoki botni groupga qo'shib, /start yuboring.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(GroupSetupStates.waiting_for_group_id)
    await callback.answer()


# =============================================================================
# Add Destination Group
# =============================================================================

@router.callback_query(F.data == "group_add_dest")
async def callback_add_dest_group(callback: CallbackQuery, state: FSMContext):
    """Destination group qo'shishni boshlash."""
    user_id = callback.from_user.id

    # Check if user has account
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

    await state.update_data(group_type="destination")

    await callback.message.edit_text(
        "➕ *Destination Group Qo'shish*\n\n"
        "Destination group - forward qilinadigan group.\n\n"
        "Group ID yoki username yuboring:\n"
        "• Username: @groupname\n"
        "• ID: -1001234567890",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(GroupSetupStates.waiting_for_group_id)
    await callback.answer()


# =============================================================================
# Process Group ID/Username
# =============================================================================

@router.message(GroupSetupStates.waiting_for_group_id)
async def process_group_id(message: Message, state: FSMContext):
    """Group ID yoki username qabul qilish."""
    input_text = message.text.strip()
    data = await state.get_data()
    group_type = data.get('group_type', 'source')

    # Get user account
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=message.from_user.id, limit=1)
        if not users:
            await message.answer("Account topilmadi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await message.answer("Account topilmadi!", reply_markup=main_menu_keyboard())
            await state.clear()
            return

        # Create Telethon client
        client = TelegramClient(
            StringSession(account.session_string),
            account.api_id,
            account.api_hash
        )

        try:
            await message.answer("🔍 Group qidirilmoqda...")

            await client.connect()

            # Get group entity
            try:
                # Try as username first
                if input_text.startswith('@'):
                    entity = await client.get_entity(input_text)
                else:
                    # Try as ID
                    group_id = validate_telegram_id(input_text)
                    if group_id:
                        entity = await client.get_entity(group_id)
                    else:
                        await message.answer(
                            "❌ ID formati noto'g'ri!\n\n"
                            "Format: -1001234567890 yoki @username",
                            reply_markup=cancel_keyboard()
                        )
                        return

                # Check if group already exists
                existing = await group_repo.get_multi(
                    account_id=account.id,
                    telegram_id=entity.id,
                    limit=1
                )
                if existing:
                    await message.answer(
                        f"⚠️ Bu group allaqachon qo'shilgan!\n\n"
                        f"📱 {entity.title}\n"
                        f"🆔 {entity.id}",
                        reply_markup=main_menu_keyboard()
                    )
                    await state.clear()
                    return

                # Add group to database
                group = await group_repo.create(
                    account_id=account.id,
                    telegram_id=entity.id,
                    access_hash=getattr(entity, 'access_hash', None),
                    title=entity.title,
                    username=getattr(entity, 'username', None),
                    group_type=GroupType.SOURCE if group_type == 'source' else GroupType.DESTINATION,
                    is_active=True,
                    member_count=getattr(entity, 'participants_count', None),
                    is_verified=getattr(entity, 'verified', False)
                )

                await session.commit()

                type_emoji = "📥" if group_type == 'source' else "📤"
                type_name = "Source" if group_type == 'source' else "Destination"

                await message.answer(
                    f"✅ *Group qo'shildi!*\n\n"
                    f"{type_emoji} Type: {type_name}\n"
                    f"📱 Nom: {entity.title}\n"
                    f"🆔 ID: {entity.id}\n"
                    f"👥 A'zolar: {getattr(entity, 'participants_count', 'N/A')}",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
                await state.clear()

            except ValueError as e:
                logger.error(f"Entity not found: {e}")
                await message.answer(
                    "❌ Group topilmadi!\n\n"
                    "Sabablari:\n"
                    "• Group private va siz a'zo emassiz\n"
                    "• ID yoki username noto'g'ri\n"
                    "• Bot groupda emas\n\n"
                    "Qayta urinib ko'ring:",
                    reply_markup=cancel_keyboard()
                )

        except Exception as e:
            logger.error(f"Error adding group: {e}", exc_info=True)
            await message.answer(
                f"❌ Xatolik: {str(e)}\n\n"
                "/start dan qayta boshlang.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()

        finally:
            await client.disconnect()


# =============================================================================
# List Groups
# =============================================================================

@router.callback_query(F.data == "group_list")
async def callback_list_groups(callback: CallbackQuery):
    """Barcha grouplarni ko'rsatish."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        # Get all groups
        groups = await group_repo.get_multi(account_id=account.id, limit=100)

        if not groups:
            await callback.message.edit_text(
                "📱 Hali hech qanday group qo'shilmagan.\n\n"
                "Groups qo'shish uchun:\n"
                "➕ Add Source/Destination",
                reply_markup=group_menu_keyboard()
            )
            await callback.answer()
            return

        # Separate by type
        source_groups = [g for g in groups if g.group_type == GroupType.SOURCE]
        dest_groups = [g for g in groups if g.group_type == GroupType.DESTINATION]

        text = "📱 *Your Groups*\n\n"

        if source_groups:
            text += "📥 *Source Groups:*\n"
            for g in source_groups:
                status = "🟢" if g.is_active else "🔴"
                text += f"{status} {g.title}\n   ID: `{g.telegram_id}`\n"
            text += "\n"

        if dest_groups:
            text += "📤 *Destination Groups:*\n"
            for g in dest_groups:
                status = "🟢" if g.is_active else "🔴"
                text += f"{status} {g.title}\n   ID: `{g.telegram_id}`\n"
            text += "\n"

        text += f"\n*Total:* {len(groups)} groups"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard()
        )

    await callback.answer()


# =============================================================================
# Remove Group
# =============================================================================

@router.callback_query(F.data == "group_remove")
async def callback_remove_group_start(callback: CallbackQuery, state: FSMContext):
    """Group o'chirishni boshlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        # Get all groups
        groups = await group_repo.get_multi(account_id=account.id, limit=100)

        if not groups:
            await callback.answer("Hech qanday group yo'q!", show_alert=True)
            return

        # Create inline keyboard with groups
        keyboard = []
        for g in groups:
            type_emoji = "📥" if g.group_type == GroupType.SOURCE else "📤"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{type_emoji} {g.title[:30]}",
                    callback_data=f"remove_group_{g.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_groups")])

        await callback.message.edit_text(
            "🗑 *O'chirish uchun group tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("remove_group_"))
async def callback_remove_group_confirm(callback: CallbackQuery):
    """Group o'chirishni tasdiqlash."""
    group_id = int(callback.data.split("_")[2])

    async with get_async_session() as session:
        group_repo = BaseRepository(Group, session)

        group = await group_repo.get(group_id)
        if not group:
            await callback.answer("Group topilmadi!", show_alert=True)
            return

        # Delete group
        await group_repo.delete(group_id)
        await session.commit()

        await callback.message.edit_text(
            f"✅ *Group o'chirildi!*\n\n"
            f"📱 {group.title}\n"
            f"🆔 {group.telegram_id}",
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard()
        )

    await callback.answer()
