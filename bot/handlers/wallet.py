"""Wallet handler for Telegram bot interface."""

import logging
from decimal import Decimal
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import TEXT

from services.payment.wallet_service import WalletService, BalanceInfo
from core.enums import TransactionType, PaymentMethod
from bot.config import settings, pricing_settings
from bot.utils.decorators import user_required, admin_required
from bot.utils.helpers import format_currency, format_datetime

logger = logging.getLogger(__name__)


class WalletHandler:
    """Handler for wallet-related bot interactions."""

    @staticmethod
    @user_required
    async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show wallet balance and options."""
        user = context.user_data.get('user')

        try:
            balance_info = WalletService.get_balance_info(user)

            # Format balance information
            balance_text = (
                f"=° <b>Your Wallet</b>\n\n"
                f"=µ <b>Current Balance:</b> {format_currency(balance_info.current_balance)}\n"
                f"=È <b>Total Credited:</b> {format_currency(balance_info.total_credited)}\n"
                f"=É <b>Total Spent:</b> {format_currency(balance_info.total_debited)}\n\n"
                f"=Ê <b>Today's Spending:</b> {format_currency(balance_info.daily_spent)}\n"
                f"=Ê <b>This Month:</b> {format_currency(balance_info.monthly_spent)}\n\n"
            )

            if balance_info.daily_limit:
                balance_text += f"ð <b>Daily Limit:</b> {format_currency(balance_info.daily_limit)}\n"

            if balance_info.monthly_limit:
                balance_text += f"=Å <b>Monthly Limit:</b> {format_currency(balance_info.monthly_limit)}\n\n"

            # Status indicator
            status_emoji = "" if balance_info.is_active else "L"
            status_text = "Active" if balance_info.is_active else "Inactive"
            balance_text += f"{status_emoji} <b>Status:</b> {status_text}"

            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("=³ Add Money", callback_data="wallet_add_money"),
                    InlineKeyboardButton("=Ê History", callback_data="wallet_history")
                ],
                [
                    InlineKeyboardButton("=È Statistics", callback_data="wallet_stats"),
                    InlineKeyboardButton("™ Settings", callback_data="wallet_settings")
                ],
                [InlineKeyboardButton("= Back", callback_data="main_menu")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    balance_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    balance_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"Error showing wallet for user {user.id}: {e}")
            error_text = "L Error loading wallet information. Please try again later."

            if update.callback_query:
                await update.callback_query.answer(error_text, show_alert=True)
            else:
                await update.message.reply_text(error_text)

    @staticmethod
    @user_required
    async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show transaction history."""
        user = context.user_data.get('user')
        page = int(context.user_data.get('wallet_history_page', 0))

        try:
            # Get transactions with pagination
            limit = 10
            offset = page * limit
            transactions = WalletService.get_transaction_history(
                user=user,
                limit=limit + 1,  # Get one extra to check if there are more
                offset=offset
            )

            has_more = len(transactions) > limit
            if has_more:
                transactions = transactions[:limit]

            if not transactions:
                history_text = "=Ý <b>Transaction History</b>\n\nL No transactions found."
            else:
                history_text = "=Ý <b>Transaction History</b>\n\n"

                for txn in transactions:
                    # Transaction type emoji
                    if txn.type in [TransactionType.CREDIT.value, TransactionType.BONUS.value, TransactionType.REFUND.value]:
                        type_emoji = "=°"
                        amount_sign = "+"
                    else:
                        type_emoji = "=¸"
                        amount_sign = "-"

                    # Status emoji
                    status_emoji = "" if txn.is_completed else "ó"

                    history_text += (
                        f"{type_emoji} <b>{txn.get_type_display()}</b> {status_emoji}\n"
                        f"=µ {amount_sign}{format_currency(txn.amount)}\n"
                        f"=Å {format_datetime(txn.created_at)}\n"
                        f"=Ý {txn.description}\n\n"
                    )

            # Create navigation keyboard
            keyboard = []
            nav_row = []

            if page > 0:
                nav_row.append(InlineKeyboardButton(" Previous", callback_data="wallet_history_prev"))

            if has_more:
                nav_row.append(InlineKeyboardButton("Next ¡", callback_data="wallet_history_next"))

            if nav_row:
                keyboard.append(nav_row)

            keyboard.extend([
                [
                    InlineKeyboardButton("= Filter", callback_data="wallet_history_filter"),
                    InlineKeyboardButton("=Ê Export", callback_data="wallet_history_export")
                ],
                [InlineKeyboardButton("= Back to Wallet", callback_data="wallet_main")]
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                history_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error showing transaction history for user {user.id}: {e}")
            await update.callback_query.answer("L Error loading transaction history", show_alert=True)

    @staticmethod
    @user_required
    async def show_wallet_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show wallet statistics."""
        user = context.user_data.get('user')

        try:
            # Get spending summaries for different periods
            summary_7d = WalletService.get_spending_summary(user, days=7)
            summary_30d = WalletService.get_spending_summary(user, days=30)
            summary_90d = WalletService.get_spending_summary(user, days=90)

            stats_text = (
                f"=Ê <b>Wallet Statistics</b>\n\n"
                f"=° <b>Current Balance:</b> {format_currency(summary_30d['current_balance'])}\n\n"
                f"=Å <b>Last 7 Days:</b>\n"
                f"   =¸ Spent: {format_currency(summary_7d['total_spent'])}\n"
                f"   =Ê Transactions: {summary_7d['transaction_count']}\n"
                f"   =È Daily Avg: {format_currency(summary_7d['daily_average'])}\n\n"
                f"=Å <b>Last 30 Days:</b>\n"
                f"   =¸ Spent: {format_currency(summary_30d['total_spent'])}\n"
                f"   =Ê Transactions: {summary_30d['transaction_count']}\n"
                f"   =È Daily Avg: {format_currency(summary_30d['daily_average'])}\n\n"
                f"=Å <b>Last 90 Days:</b>\n"
                f"   =¸ Spent: {format_currency(summary_90d['total_spent'])}\n"
                f"   =Ê Transactions: {summary_90d['transaction_count']}\n"
                f"   =È Daily Avg: {format_currency(summary_90d['daily_average'])}\n"
            )

            keyboard = [
                [InlineKeyboardButton("= Back to Wallet", callback_data="wallet_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                stats_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error showing wallet statistics for user {user.id}: {e}")
            await update.callback_query.answer("L Error loading statistics", show_alert=True)

    @staticmethod
    @user_required
    async def show_add_money_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show payment method options."""
        keyboard = [
            [
                InlineKeyboardButton("=³ PayMe", callback_data="payment_payme"),
                InlineKeyboardButton("<æ Click", callback_data="payment_click")
            ],
            [InlineKeyboardButton("= Back to Wallet", callback_data="wallet_main")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        add_money_text = (
            f"=³ <b>Add Money to Wallet</b>\n\n"
            f"=° <b>Minimum Amount:</b> {format_currency(pricing_settings.min_payment_amount)}\n"
            f"=° <b>Maximum Amount:</b> {format_currency(pricing_settings.max_payment_amount)}\n\n"
            f"Please select a payment method:"
        )

        await update.callback_query.edit_message_text(
            add_money_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    @staticmethod
    @admin_required
    async def admin_adjust_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin function to adjust user balance."""
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "Usage: /adjust_balance <user_id> <amount> <description>\n"
                "Example: /adjust_balance 123456789 1000 \"Bonus for testing\""
            )
            return

        try:
            user_id = int(context.args[0])
            amount = Decimal(context.args[1])
            description = " ".join(context.args[2:])

            from django_admin.apps.users.models import User
            target_user = User.objects.get(telegram_id=user_id)

            if amount > 0:
                result = WalletService.add_balance(
                    user=target_user,
                    amount=amount,
                    description=f"Admin adjustment: {description}",
                    payment_method=PaymentMethod.ADMIN
                )
            else:
                result = WalletService.deduct_balance(
                    user=target_user,
                    amount=abs(amount),
                    description=f"Admin adjustment: {description}",
                    skip_balance_check=True
                )

            if result.success:
                balance_info = WalletService.get_balance_info(target_user)
                await update.message.reply_text(
                    f" Balance adjusted successfully!\n\n"
                    f"User: {target_user.first_name} ({user_id})\n"
                    f"Amount: {format_currency(amount)}\n"
                    f"New Balance: {format_currency(balance_info.current_balance)}\n"
                    f"Description: {description}"
                )

                # Notify user about balance change
                try:
                    sign = "+" if amount > 0 else ""
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"=° Your wallet balance has been updated!\n\n"
                             f"Change: {sign}{format_currency(amount)}\n"
                             f"New Balance: {format_currency(balance_info.current_balance)}\n"
                             f"Reason: {description}"
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {user_id} about balance change: {e}")
            else:
                await update.message.reply_text(f"L Error adjusting balance: {result.error}")

        except ValueError:
            await update.message.reply_text("L Invalid user ID or amount format")
        except Exception as e:
            logger.error(f"Error adjusting balance: {e}")
            await update.message.reply_text("L Error adjusting balance. Please try again.")

    @staticmethod
    async def handle_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet-related callback queries."""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "wallet_main":
            await WalletHandler.show_wallet(update, context)
        elif callback_data == "wallet_history":
            context.user_data['wallet_history_page'] = 0
            await WalletHandler.show_transaction_history(update, context)
        elif callback_data == "wallet_history_prev":
            current_page = context.user_data.get('wallet_history_page', 0)
            context.user_data['wallet_history_page'] = max(0, current_page - 1)
            await WalletHandler.show_transaction_history(update, context)
        elif callback_data == "wallet_history_next":
            current_page = context.user_data.get('wallet_history_page', 0)
            context.user_data['wallet_history_page'] = current_page + 1
            await WalletHandler.show_transaction_history(update, context)
        elif callback_data == "wallet_stats":
            await WalletHandler.show_wallet_statistics(update, context)
        elif callback_data == "wallet_add_money":
            await WalletHandler.show_add_money_options(update, context)


def register_wallet_handlers(application):
    """Register wallet-related handlers."""
    application.add_handler(CallbackQueryHandler(
        WalletHandler.handle_wallet_callback,
        pattern=r"^wallet_"
    ))