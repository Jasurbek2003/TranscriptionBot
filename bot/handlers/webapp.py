# bot/handlers/webapp.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton

from bot.config import settings
import logging

logger = logging.getLogger(__name__)

router = Router()


def get_webapp_keyboard():
    """Get inline keyboard with webapp button"""
    builder = InlineKeyboardBuilder()

    # Main webapp button
    builder.row(
        InlineKeyboardButton(
            text="🌐 Open Web App",
            web_app=WebAppInfo(url=settings.webapp_url)
        )
    )

    # Quick action buttons
    builder.row(
        InlineKeyboardButton(
            text="📤 Upload File",
            web_app=WebAppInfo(url=f"{settings.webapp_url}/upload")
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 View History",
            web_app=WebAppInfo(url=f"{settings.webapp_url}/transcriptions")
        )
    )

    return builder.as_markup()


def get_webapp_menu_button():
    """Get reply keyboard with webapp button"""
    builder = ReplyKeyboardBuilder()

    # Webapp menu button
    builder.row(
        KeyboardButton(
            text="🌐 Open Web App",
            web_app=WebAppInfo(url=settings.webapp_url)
        )
    )

    # Regular buttons
    builder.row(
        KeyboardButton(text="💰 My Balance"),
        KeyboardButton(text="ℹ️ Help")
    )

    return builder.as_markup(resize_keyboard=True)


@router.message(Command("webapp"))
async def cmd_webapp(message: Message):
    """Handle /webapp command"""
    await message.answer(
        "🌐 <b>Web Application</b>\n\n"
        "Access the full web interface with advanced features:\n\n"
        "✨ <b>Features:</b>\n"
        "• Upload files via drag & drop\n"
        "• View transcription history\n"
        "• Manage your balance\n"
        "• Download transcriptions\n"
        "• Better mobile experience\n\n"
        "Click the button below to open:",
        reply_markup=get_webapp_keyboard()
    )


@router.message(F.text == "🌐 Open Web App")
async def webapp_button_handler(message: Message):
    """Handle webapp button from keyboard"""
    await cmd_webapp(message)


@router.message(Command("webmenu"))
async def cmd_webmenu(message: Message):
    """Set menu button with webapp"""
    await message.answer(
        "📱 <b>Web App Menu</b>\n\n"
        "Use the button below to access the web interface:",
        reply_markup=get_webapp_menu_button()
    )
