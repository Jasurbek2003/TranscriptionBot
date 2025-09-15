from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional, List


def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    """Get payment methods keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💳 Payme",
            callback_data="payment:payme"
        ),
        InlineKeyboardButton(
            text="💰 Click",
            callback_data="payment:click"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="payment:cancel"
        )
    )

    return builder.as_markup()


def get_amount_keyboard(amounts: List[int] = None) -> InlineKeyboardMarkup:
    """Get predefined amounts keyboard"""
    if amounts is None:
        amounts = [5000, 10000, 20000, 50000, 100000]

    builder = InlineKeyboardBuilder()

    # Add amount buttons (2 per row)
    for i in range(0, len(amounts), 2):
        row_buttons = []
        for j in range(i, min(i + 2, len(amounts))):
            row_buttons.append(
                InlineKeyboardButton(
                    text=f"{amounts[j]:,} UZS",
                    callback_data=f"amount:{amounts[j]}"
                )
            )
        builder.row(*row_buttons)

    # Custom amount button
    builder.row(
        InlineKeyboardButton(
            text="✏️ Enter custom amount",
            callback_data="amount:custom"
        )
    )

    # Cancel button
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="amount:cancel"
        )
    )

    return builder.as_markup()


def get_payment_confirmation_keyboard(
        amount: float,
        payment_method: str,
        transaction_id: str
) -> InlineKeyboardMarkup:
    """Get payment confirmation keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ I have paid",
            callback_data=f"confirm_payment:{transaction_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel payment",
            callback_data=f"cancel_payment:{transaction_id}"
        )
    )

    return builder.as_markup()
