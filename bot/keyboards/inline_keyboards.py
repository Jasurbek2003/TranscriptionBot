from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_balance_keyboard() -> InlineKeyboardMarkup:
    """Get balance actions keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💳 Top Up",
            callback_data="action:topup"
        ),
        InlineKeyboardButton(
            text="📊 History",
            callback_data="action:history"
        )
    )

    return builder.as_markup()


def get_transcription_keyboard(
        transcription_id: str,
        can_retry: bool = True
) -> InlineKeyboardMarkup:
    """Get transcription actions keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📄 Download",
            callback_data=f"download:{transcription_id}"
        )
    )

    if can_retry:
        builder.row(
            InlineKeyboardButton(
                text="🔄 Retry",
                callback_data=f"retry:{transcription_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⭐ Rate",
            callback_data=f"rate:{transcription_id}"
        )
    )

    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🌐 Language",
            callback_data="settings:language"
        ),
        InlineKeyboardButton(
            text="🔔 Notifications",
            callback_data="settings:notifications"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Transcription Settings",
            callback_data="settings:transcription"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back",
            callback_data="settings:back"
        )
    )

    return builder.as_markup()


def get_language_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    builder = InlineKeyboardBuilder()

    languages = [
        ("🇬🇧 English", "en"),
        ("🇷🇺 Русский", "ru"),
        ("🇺🇿 O'zbek", "uz")
    ]

    for name, code in languages:
        if code == current_lang:
            name = f"✅ {name}"
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=f"lang:{code}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back",
            callback_data="lang:back"
        )
    )

    return builder.as_markup()


def get_pagination_keyboard(
        current_page: int,
        total_pages: int,
        callback_prefix: str
) -> InlineKeyboardMarkup:
    """Get pagination keyboard"""
    builder = InlineKeyboardBuilder()

    buttons = []

    # Previous button
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"{callback_prefix}:page:{current_page - 1}"
            )
        )

    # Page indicator
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data=f"{callback_prefix}:page:current"
        )
    )

    # Next button
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"{callback_prefix}:page:{current_page + 1}"
            )
        )

    builder.row(*buttons)

    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin panel keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 Statistics",
            callback_data="admin:stats"
        ),
        InlineKeyboardButton(
            text="👥 Users",
            callback_data="admin:users"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Transactions",
            callback_data="admin:transactions"
        ),
        InlineKeyboardButton(
            text="⚙️ Settings",
            callback_data="admin:settings"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Broadcast",
            callback_data="admin:broadcast"
        ),
        InlineKeyboardButton(
            text="🔧 Maintenance",
            callback_data="admin:maintenance"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 Reports",
            callback_data="admin:reports"
        ),
        InlineKeyboardButton(
            text="🎯 Pricing",
            callback_data="admin:pricing"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back to Bot",
            callback_data="admin:exit"
        )
    )

    return builder.as_markup()


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Get rating keyboard"""
    builder = InlineKeyboardBuilder()

    # Star ratings
    for i in range(1, 6):
        builder.add(
            InlineKeyboardButton(
                text="⭐" * i,
                callback_data=f"rating:{i}"
            )
        )

    builder.adjust(5)  # All stars in one row

    builder.row(
        InlineKeyboardButton(
            text="Skip",
            callback_data="rating:skip"
        )
    )

    return builder.as_markup()
