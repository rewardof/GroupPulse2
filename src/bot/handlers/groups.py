"""
Group Management Handlers

Destination group qo'shish, ko'rish, o'chirish.
Userbot accountning BARCHA grouplaridan avtomatik listen qiladi.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.bot.states.account_setup import GroupSetupStates
from src.bot.keyboards.main import group_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.base import BaseRepository
from src.database.repositories.account_repo import AccountRepository
from src.database.models import User, TelegramAccount, Group
from src.utils.validators import validate_telegram_id
from telethon import TelegramClient
from telethon.sessions import StringSession
from config.settings import settings
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
        "🤖 Bot sizning accountingizdagi *barcha* grouplardan listen qiladi.\n\n"
        "📤 *Destination Group* - Forward qilinadigan group (faqat 1ta).\n\n"
        "Nima qilmoqchisiz?",
        parse_mode="Markdown",
        reply_markup=group_menu_keyboard()
    )
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
        group_repo = BaseRepository(Group, session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Avval account qo'shing!", show_alert=True)
            return

        # Check if already has destination group
        existing_group = await group_repo.get_multi(account_id=account.id, limit=1)
        if existing_group:
            await callback.answer(
                "Sizda allaqachon destination group bor!\n"
                "Avval uni o'chiring, keyin yangisini qo'shing.",
                show_alert=True
            )
            return

    await callback.message.edit_text(
        "➕ *Destination Group Qo'shish*\n\n"
        "Bu yerga forward qilinadi.\n\n"
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
async def process_group_id(message: Message, state: FSMContext, userbot_manager=None):
    """Group ID yoki username qabul qilish."""
    input_text = message.text.strip()

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

        # Check if already has destination group
        existing_group = await group_repo.get_multi(account_id=account.id, limit=1)
        if existing_group:
            await message.answer(
                "⚠️ Sizda allaqachon destination group bor!\n\n"
                f"📱 {existing_group[0].title}\n\n"
                "Avval uni o'chiring.",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()
            return

        # Create Telethon client
        client = TelegramClient(
            StringSession(account.session_string),
            settings.API_ID,
            settings.API_HASH
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

                # Add group to database
                group = await group_repo.create(
                    account_id=account.id,
                    telegram_id=entity.id,
                    access_hash=getattr(entity, 'access_hash', None),
                    title=entity.title,
                    username=getattr(entity, 'username', None),
                    is_active=True,
                    member_count=getattr(entity, 'participants_count', None),
                    is_verified=getattr(entity, 'verified', False)
                )

                await session.commit()

                # ✅ Reload destination group in userbot manager
                if userbot_manager:
                    await userbot_manager.reload_account_destination(account.id)
                    logger.info(f"Reloaded destination for account {account.id}")

                await message.answer(
                    f"✅ *Destination Group qo'shildi!*\n\n"
                    f"📤 {entity.title}\n"
                    f"🆔 ID: {entity.id}\n"
                    f"👥 A'zolar: {getattr(entity, 'participants_count', 'N/A')}\n\n"
                    "🤖 Bot accountingizdagi *barcha* grouplardan listen qiladi.\n"
                    "📨 Keywordlarga mos kelgan messagelar bu groupga forward qilinadi.",
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
# View Destination Group
# =============================================================================

@router.callback_query(F.data == "group_list")
async def callback_list_groups(callback: CallbackQuery):
    """Destination groupni ko'rsatish."""
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

        # Get destination group
        groups = await group_repo.get_multi(account_id=account.id, limit=1)

        if not groups:
            await callback.message.edit_text(
                "📱 Hali destination group qo'shilmagan.\n\n"
                "Destination group qo'shish uchun:\n"
                "➕ Add Destination",
                reply_markup=group_menu_keyboard()
            )
            await callback.answer()
            return

        group = groups[0]
        status = "🟢" if group.is_active else "🔴"

        text = (
            f"📱 *Destination Group*\n\n"
            f"{status} {group.title}\n"
            f"🆔 ID: `{group.telegram_id}`\n"
            f"👥 A'zolar: {group.member_count or 'N/A'}\n"
            f"📨 Forward: {group.total_messages_forwarded}\n\n"
            f"🤖 Bot accountingizdagi *barcha* grouplardan listen qiladi.\n"
            f"📤 Keywordlarga mos messagelar bu groupga forward qilinadi."
        )

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard()
        )

    await callback.answer()


# =============================================================================
# Remove Destination Group
# =============================================================================

@router.callback_query(F.data == "group_remove")
async def callback_remove_group(callback: CallbackQuery):
    """Destination groupni o'chirish."""
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

        # Get destination group
        groups = await group_repo.get_multi(account_id=account.id, limit=1)

        if not groups:
            await callback.answer("Destination group yo'q!", show_alert=True)
            return

        group = groups[0]

        # Confirm deletion
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_remove_group_{group.id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="menu_groups")
            ]
        ])

        await callback.message.edit_text(
            f"⚠️ *Ogohantirish*\n\n"
            f"Destination groupni o'chirmoqchisiz:\n\n"
            f"📱 {group.title}\n"
            f"🆔 {group.telegram_id}\n\n"
            f"Ishonchingiz komilmi?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_remove_group_"))
async def callback_confirm_remove_group(callback: CallbackQuery, userbot_manager=None):
    """Destination group o'chirishni tasdiqlash."""
    group_id = int(callback.data.split("_")[3])

    async with get_async_session() as session:
        group_repo = BaseRepository(Group, session)

        group = await group_repo.get(group_id)
        if not group:
            await callback.answer("Group topilmadi!", show_alert=True)
            return

        # Store account_id before deletion
        account_id = group.account_id

        # Delete group
        await group_repo.delete(group_id)
        await session.commit()

        # ✅ Reload destination group in userbot manager
        if userbot_manager:
            await userbot_manager.reload_account_destination(account_id)
            logger.info(f"Removed destination for account {account_id}")

        await callback.message.edit_text(
            f"✅ *Destination group o'chirildi!*\n\n"
            f"📱 {group.title}\n"
            f"🆔 {group.telegram_id}",
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard()
        )

    await callback.answer()
