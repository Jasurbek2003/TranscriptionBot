"""Balance and wallet handlers for showing user balance and transaction history."""

import logging

from aiogram import F, Router
from aiogram.types import Message

from services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text.in_(["/balance", "💰 Balance", "💰 My Balance"]))
async def show_balance(message: Message, user, wallet):
    """Show user balance and wallet information."""
    try:
        wallet_service = WalletService()
        balance_info = await wallet_service.get_balance_info(user)

        balance_text = (
            f"💰 <b>Your Balance</b>\n\n"
            f"💳 Current Balance: <b>{balance_info.current_balance:,.2f} UZS</b>\n"
            f"📈 Total Added: {balance_info.total_credited:,.2f} UZS\n"
            f"📉 Total Spent: {balance_info.total_debited:,.2f} UZS\n\n"
            f"💡 <i>Use /topup to add funds to your account</i>"
        )

        await message.answer(balance_text)

    except Exception as e:
        logger.error(f"Error showing balance for user {user.id}: {e}")
        await message.answer("❌ Error loading balance information. Please try again later.")


@router.message(F.text.in_(["/history", "📊 History", "📊 Transaction History"]))
async def show_transaction_history(message: Message, user):
    """Show user transaction history."""
    try:
        wallet_service = WalletService()
        transactions = await wallet_service.get_transaction_history(user, limit=10)

        if not transactions:
            await message.answer(
                "📊 <b>Transaction History</b>\n\n"
                "❌ No transactions found.\n\n"
                "💡 Start by sending an audio or video file for transcription!"
            )
            return

        history_text = "📊 <b>Transaction History</b>\n\n"

        for trans in transactions:
            # Transaction type emoji
            if trans.type == "credit":
                type_emoji = "💰"
                amount_text = f"+{trans.amount:.2f}"
            else:
                type_emoji = "💸"
                amount_text = f"-{trans.amount:.2f}"

            # Status emoji
            status_emoji = "✅" if trans.status == "completed" else "⏳"

            history_text += (
                f"{type_emoji} <b>{amount_text} UZS</b> {status_emoji}\n"
                f"📝 {trans.description}\n"
                f"📅 {trans.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )

        if len(transactions) == 10:
            history_text += "💡 <i>Showing last 10 transactions</i>"

        await message.answer(history_text)

    except Exception as e:
        logger.error(f"Error showing history for user {user.id}: {e}")
        await message.answer("❌ Error loading transaction history. Please try again later.")

# Topup handler removed - now handled in payment.py with Click and Payme integration
