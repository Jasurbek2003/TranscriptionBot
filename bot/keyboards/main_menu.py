from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from bot.config import settings


def get_main_menu(is_admin: bool = False, include_webapp: bool = True) -> ReplyKeyboardMarkup:
    """Get main menu keyboard"""
    builder = ReplyKeyboardBuilder()

    # Webapp button (optional)
    if include_webapp:
        builder.row(
            KeyboardButton(
                text="🌐 Open Web App",
                web_app=WebAppInfo(url=settings.webapp_url)
            )
        )

    # Main buttons
    builder.row(
        KeyboardButton(text="📎 Send Media"),
        KeyboardButton(text="💰 My Balance")
    )
    builder.row(
        KeyboardButton(text="💳 Top Up"),
        KeyboardButton(text="📊 History")
    )
    builder.row(
        KeyboardButton(text="⚙️ Settings"),
        KeyboardButton(text="ℹ️ Help")
    )

    # Admin button
    if is_admin:
        builder.row(KeyboardButton(text="👨‍💼 Admin Panel"))

    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Get cancel keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Cancel"))
    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Get back keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⬅️ Back"))
    return builder.as_markup(resize_keyboard=True)


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Get confirmation keyboard"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Confirm"),
        KeyboardButton(text="❌ Cancel")
    )
    return builder.as_markup(resize_keyboard=True)
