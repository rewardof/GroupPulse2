"""
Account Management Handlers

Telegram account qo'shish, ko'rish, o'chirish.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError, FloodWaitError
from src.bot.states.account_setup import AccountSetupStates
from src.bot.keyboards.main import account_menu_keyboard, main_menu_keyboard, cancel_keyboard
from src.database.connection import get_async_session
from src.database.repositories.account_repo import AccountRepository
from src.database.repositories.base import BaseRepository
from src.database.models import User, TelegramAccount
from src.utils.validators import validate_phone_number, validate_api_credentials
import logging

logger = logging.getLogger(__name__)

router = Router()


# =============================================================================
# Account Menu
# =============================================================================

@router.callback_query(F.data == "menu_account")
async def callback_account_menu(callback: CallbackQuery):
    """Account menu ni ko'rsatish."""
    user_id = callback.from_user.id

    # Check if user has account
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        user = await user_repo.get_multi(telegram_id=user_id, limit=1)
        has_account = False

        if user:
            account = await account_repo.get_by_user_id(user[0].id)
            has_account = account is not None

    await callback.message.edit_text(
        "🔐 *Account Management*\n\n"
        f"Status: {'✅ Connected' if has_account else '❌ Not connected'}\n\n"
        "Choose an option:",
        parse_mode="Markdown",
        reply_markup=account_menu_keyboard(has_account)
    )
    await callback.answer()


# =============================================================================
# Add Account Flow
# =============================================================================

@router.callback_query(F.data == "account_add")
async def callback_add_account(callback: CallbackQuery, state: FSMContext):
    """Account qo'shish jarayonini boshlash."""
    user_id = callback.from_user.id

    # Check if already has account
    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if users:
            account = await account_repo.get_by_user_id(users[0].id)
            if account:
                await callback.answer("Sizda allaqachon account bor!", show_alert=True)
                return

    await callback.message.edit_text(
        "🔐 *Telegram Account Qo'shish*\n\n"
        "Birinchi navbatda, API credentials kerak.\n\n"
        "1. https://my.telegram.org ga kiring\n"
        "2. 'API development tools' ga o'ting\n"
        "3. App yarating va API ID/Hash oling\n\n"
        "Endi *API ID* ni yuboring:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AccountSetupStates.waiting_for_api_id)
    await callback.answer()


@router.message(AccountSetupStates.waiting_for_api_id)
async def process_api_id(message: Message, state: FSMContext):
    """API ID ni qabul qilish."""
    try:
        api_id = int(message.text.strip())
        await state.update_data(api_id=api_id)

        await message.answer(
            "✅ API ID qabul qilindi!\n\n"
            "Endi *API Hash* ni yuboring:",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(AccountSetupStates.waiting_for_api_hash)

    except ValueError:
        await message.answer(
            "❌ Xato! API ID raqam bo'lishi kerak.\n\n"
            "Qaytadan yuboring:",
            reply_markup=cancel_keyboard()
        )


@router.message(AccountSetupStates.waiting_for_api_hash)
async def process_api_hash(message: Message, state: FSMContext):
    """API Hash ni qabul qilish."""
    api_hash = message.text.strip()
    data = await state.get_data()

    # Validate credentials format
    if not validate_api_credentials(str(data['api_id']), api_hash):
        await message.answer(
            "❌ API credentials formati noto'g'ri.\n\n"
            "API Hash 32 ta hex belgi bo'lishi kerak.\n\n"
            "Qaytadan yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(api_hash=api_hash)

    await message.answer(
        "✅ API Hash qabul qilindi!\n\n"
        "Endi telefon raqamingizni yuboring.\n"
        "Format: *+998901234567*\n\n"
        "Mamlakat kodi bilan (+) belgisi bilan:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AccountSetupStates.waiting_for_phone)


@router.message(AccountSetupStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Telefon raqamni qabul qilish va kod yuborish."""
    phone = message.text.strip()

    # Validate phone
    if not validate_phone_number(phone):
        await message.answer(
            "❌ Telefon raqam formati noto'g'ri!\n\n"
            "Format: +998901234567\n\n"
            "Qaytadan yuboring:",
            reply_markup=cancel_keyboard()
        )
        return

    data = await state.get_data()

    # Create temporary Telethon client to send code
    client = TelegramClient(
        StringSession(),
        data['api_id'],
        data['api_hash']
    )

    try:
        await message.answer("📡 Telegram'ga ulanmoqda...")

        await client.connect()
        result = await client.send_code_request(phone)

        # Save session and data
        temp_session = client.session.save()
        await state.update_data(
            phone=phone,
            temp_session=temp_session,
            phone_code_hash=result.phone_code_hash
        )

        await message.answer(
            "✅ Tasdiqlash kodi yuborildi!\n\n"
            f"Telegram'ga kelgan kodni yuboring:\n"
            f"(Telefon: {phone})",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(AccountSetupStates.waiting_for_code)

    except FloodWaitError as e:
        await message.answer(
            f"⏳ FloodWait: {e.seconds} soniya kuting.\n\n"
            "Qaytadan urinib ko'ring.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error sending code: {e}", exc_info=True)
        await message.answer(
            f"❌ Xatolik: {str(e)}\n\n"
            "API credentials yoki telefon raqamni tekshiring.\n"
            "/start dan qayta boshlang.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    finally:
        await client.disconnect()


@router.message(AccountSetupStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    """Tasdiqlash kodini qabul qilish."""
    code = message.text.strip().replace("-", "").replace(" ", "")
    data = await state.get_data()

    # Recreate client
    client = TelegramClient(
        StringSession(data['temp_session']),
        data['api_id'],
        data['api_hash']
    )

    try:
        await message.answer("🔐 Tekshirilmoqda...")

        await client.connect()

        # Try to sign in
        try:
            await client.sign_in(data['phone'], code)

            # Success! Save to database
            session_string = client.session.save()

            async with get_async_session() as session:
                user_repo = BaseRepository(User, session)
                account_repo = AccountRepository(session)

                # Get or create user
                users = await user_repo.get_multi(telegram_id=message.from_user.id, limit=1)
                if users:
                    user = users[0]
                else:
                    user = await user_repo.create(
                        telegram_id=message.from_user.id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        last_name=message.from_user.last_name
                    )

                # Create account
                account = await account_repo.create(
                    user_id=user.id,
                    phone_number=data['phone'],
                    api_id=data['api_id'],
                    api_hash=data['api_hash'],
                    session_string=session_string,
                    is_authorized=True,
                    is_active=True
                )

                await session.commit()

            await message.answer(
                "✅ *Account muvaffaqiyatli qo'shildi!*\n\n"
                f"📱 Telefon: {data['phone']}\n\n"
                "Endi source va destination groups qo'shishingiz mumkin.\n\n"
                "📱 Groups → ➕ Add Source/Destination",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            await state.clear()

        except SessionPasswordNeededError:
            # 2FA enabled
            await message.answer(
                "🔐 2FA (Two-Factor Authentication) yoqilgan.\n\n"
                "2FA parolingizni yuboring:",
                reply_markup=cancel_keyboard()
            )
            await state.set_state(AccountSetupStates.waiting_for_password)

        except PhoneCodeInvalidError:
            await message.answer(
                "❌ Kod noto'g'ri!\n\n"
                "Qaytadan yuboring yoki /start dan boshlang.",
                reply_markup=cancel_keyboard()
            )

    except Exception as e:
        logger.error(f"Error during sign in: {e}", exc_info=True)
        await message.answer(
            f"❌ Xatolik: {str(e)}\n\n"
            "/start dan qayta boshlang.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    finally:
        await client.disconnect()


@router.message(AccountSetupStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """2FA parolni qabul qilish."""
    password = message.text.strip()
    data = await state.get_data()

    # Recreate client
    client = TelegramClient(
        StringSession(data['temp_session']),
        data['api_id'],
        data['api_hash']
    )

    try:
        await message.answer("🔐 Tekshirilmoqda...")

        await client.connect()
        await client.sign_in(password=password)

        # Success! Save to database
        session_string = client.session.save()

        async with get_async_session() as session:
            user_repo = BaseRepository(User, session)
            account_repo = AccountRepository(session)

            # Get or create user
            users = await user_repo.get_multi(telegram_id=message.from_user.id, limit=1)
            if users:
                user = users[0]
            else:
                user = await user_repo.create(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )

            # Create account
            await account_repo.create(
                user_id=user.id,
                phone_number=data['phone'],
                api_id=data['api_id'],
                api_hash=data['api_hash'],
                session_string=session_string,
                is_authorized=True,
                is_active=True
            )

            await session.commit()

        await message.answer(
            "✅ *Account muvaffaqiyatli qo'shildi!*\n\n"
            f"📱 Telefon: {data['phone']}\n"
            "🔐 2FA: Enabled\n\n"
            "Endi groups qo'shishingiz mumkin!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Error with 2FA: {e}", exc_info=True)
        await message.answer(
            f"❌ Parol noto'g'ri: {str(e)}\n\n"
            "/start dan qayta boshlang.",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    finally:
        await client.disconnect()


# =============================================================================
# Account Info
# =============================================================================

@router.callback_query(F.data == "account_info")
async def callback_account_info(callback: CallbackQuery):
    """Account ma'lumotlarini ko'rsatish."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        status = "🟢 Active" if account.is_active else "🔴 Inactive"
        auth = "✅ Authorized" if account.is_authorized else "❌ Not Authorized"
        flood = ""
        if account.flood_wait_until:
            flood = f"\n⏳ Flood wait: {account.flood_wait_until}"

        await callback.message.edit_text(
            f"📱 *Account Information*\n\n"
            f"📞 Phone: {account.phone_number}\n"
            f"🆔 API ID: {account.api_id}\n"
            f"🔐 Status: {auth}\n"
            f"📊 State: {status}\n"
            f"📨 Messages today: {account.messages_sent_today}\n"
            f"{flood}\n\n"
            f"Created: {account.created_at.strftime('%Y-%m-%d %H:%M')}",
            parse_mode="Markdown",
            reply_markup=account_menu_keyboard(True)
        )

    await callback.answer()


# =============================================================================
# Disconnect Account
# =============================================================================

@router.callback_query(F.data == "account_disconnect")
async def callback_disconnect_account(callback: CallbackQuery):
    """Account o'chirish (tasdiqlash)."""
    await callback.message.edit_text(
        "⚠️ *Ogohantirish*\n\n"
        "Account o'chirilsa:\n"
        "• Barcha groups o'chiriladi\n"
        "• Barcha keywords o'chiriladi\n"
        "• Barcha rules o'chiriladi\n"
        "• Forwarding to'xtaydi\n\n"
        "Ishonchingiz komilmi?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_disconnect"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="menu_account")
            ]
        ])
    )
    await callback.answer()


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(F.data == "confirm_disconnect")
async def callback_confirm_disconnect(callback: CallbackQuery):
    """Account o'chirishni tasdiqlash."""
    user_id = callback.from_user.id

    async with get_async_session() as session:
        user_repo = BaseRepository(User, session)
        account_repo = AccountRepository(session)

        users = await user_repo.get_multi(telegram_id=user_id, limit=1)
        if not users:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        account = await account_repo.get_by_user_id(users[0].id)
        if not account:
            await callback.answer("Account topilmadi!", show_alert=True)
            return

        # Delete account (cascade will delete groups, keywords, rules)
        await account_repo.delete(account.id)
        await session.commit()

    await callback.message.edit_text(
        "✅ Account muvaffaqiyatli o'chirildi.\n\n"
        "Barcha ma'lumotlar tozalandi.",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()
