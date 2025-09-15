# bot/handlers/start.py

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.inline_keyboards import get_settings_keyboard, get_language_keyboard
from bot.config import settings
from bot.utils.messages import get_welcome_message, get_help_message
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet
):
    """Handle /start command"""
    # Clear any states
    await state.clear()

    # Check if user is admin
    is_admin = message.from_user.id in settings.ADMIN_IDS

    # Send welcome message
    welcome_text = get_welcome_message(
        user_name=message.from_user.first_name,
        balance=wallet.balance,
        language=user.language_code
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu(is_admin=is_admin)
    )

    logger.info(f"User {message.from_user.id} started the bot")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = get_help_message()
    await message.answer(help_text)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Show main menu"""
    is_admin = message.from_user.id in settings.ADMIN_IDS
    await message.answer(
        "📱 Main Menu",
        reply_markup=get_main_menu(is_admin=is_admin)
    )


@router.message(F.text == "ℹ️ Help")
async def help_button(message: Message):
    """Handle help button"""
    await cmd_help(message)


@router.message(F.text == "⚙️ Settings")
async def settings_button(message: Message):
    """Handle settings button"""
    await message.answer(
        "⚙️ <b>Settings</b>\n\nChoose what you want to configure:",
        reply_markup=get_settings_keyboard()
    )


@router.callback_query(F.data == "settings:language")
async def settings_language(callback: CallbackQuery, user):
    """Handle language settings"""
    await callback.message.edit_text(
        "🌐 <b>Language Settings</b>\n\nSelect your preferred language:",
        reply_markup=get_language_keyboard(user.language_code)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def change_language(
        callback: CallbackQuery,
        session: AsyncSession,
        user
):
    """Handle language change"""
    lang_code = callback.data.split(":")[1]

    if lang_code == "back":
        await callback.message.edit_text(
            "⚙️ <b>Settings</b>\n\nChoose what you want to configure:",
            reply_markup=get_settings_keyboard()
        )
    else:
        # Update user language
        user.language_code = lang_code
        await session.commit()

        # Update message
        await callback.message.edit_text(
            "✅ Language updated successfully!",
            reply_markup=get_language_keyboard(lang_code)
        )

        await callback.answer("Language updated!", show_alert=True)


@router.callback_query(F.data == "settings:notifications")
async def settings_notifications(callback: CallbackQuery):
    """Handle notification settings"""
    # TODO: Implement notification settings
    await callback.answer("Notification settings coming soon!", show_alert=True)


@router.callback_query(F.data == "settings:transcription")
async def settings_transcription(callback: CallbackQuery):
    """Handle transcription settings"""
    # TODO: Implement transcription settings
    await callback.answer("Transcription settings coming soon!", show_alert=True)


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    """Go back to main menu"""
    is_admin = callback.from_user.id in settings.ADMIN_IDS
    await callback.message.answer(
        "📱 Main Menu",
        reply_markup=get_main_menu(is_admin=is_admin)
    )
    await callback.message.delete()
    await callback.answer()
