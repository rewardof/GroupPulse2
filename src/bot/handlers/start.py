"""
Start and Help Handlers

Basic bot commands: /start and /help
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from src.bot.keyboards.main import main_menu_keyboard
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle /start command.

    Args:
        message: Telegram message
        state: FSM context
    """
    # Clear any active FSM state
    await state.clear()

    welcome_text = (
        f"👋 Welcome to *GroupPulse*!\n\n"
        f"I'm your Telegram message forwarding assistant. "
        f"I can help you:\n\n"
        f"• 🔐 Connect your Telegram account\n"
        f"• 📱 Manage source and destination groups\n"
        f"• 🔑 Set up keyword filters\n"
        f"• ⚙️ Create forwarding rules\n"
        f"• 📊 Monitor forwarding statistics\n\n"
        f"Choose an option below to get started:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handle /help command.

    Args:
        message: Telegram message
    """
    help_text = (
        "🔍 *GroupPulse Help*\n\n"
        "*Getting Started:*\n"
        "1. Connect your Telegram account via /start → Account\n"
        "2. Add source groups (groups to listen to)\n"
        "3. Add destination groups (where to forward)\n"
        "4. Create keywords (optional filters)\n"
        "5. Create forwarding rules\n\n"
        "*Commands:*\n"
        "/start - Show main menu\n"
        "/help - Show this help message\n"
        "/menu - Return to main menu\n"
        "/stats - View statistics\n\n"
        "*Features:*\n"
        "✓ Session string based (secure)\n"
        "✓ Keyword filtering (regex supported)\n"
        "✓ Rate limiting (Telegram compliant)\n"
        "✓ Human-like behavior simulation\n"
        "✓ Deduplication\n\n"
        "*Support:*\n"
        "For issues or questions, contact the developer."
    )

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """
    Handle /menu command - return to main menu.

    Args:
        message: Telegram message
        state: FSM context
    """
    await state.clear()

    await message.answer(
        "📋 *Main Menu*",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """
    Handle back to menu callback.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()

    await callback.message.edit_text(
        "📋 *Main Menu*",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def callback_help(callback: CallbackQuery):
    """
    Handle help menu callback.

    Args:
        callback: Callback query
    """
    help_text = (
        "🔍 *GroupPulse Help*\n\n"
        "Use the buttons in the main menu to:\n\n"
        "🔐 *Account* - Manage your Telegram account\n"
        "📱 *Groups* - Add/remove source and destination groups\n"
        "🔑 *Keywords* - Create keyword filters\n"
        "⚙️ *Rules* - Configure forwarding rules\n"
        "📊 *Statistics* - View forwarding stats\n\n"
        "Each section has detailed instructions."
    )

    await callback.message.edit_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Handle cancel callback - clear FSM and return to menu.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()

    await callback.message.edit_text(
        "❌ Cancelled. Returning to main menu.",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()
