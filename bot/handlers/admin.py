"""
Admin handlers - Currently disabled and needs refactoring to Django ORM.

This module uses SQLAlchemy-style queries that need to be converted to Django ORM.
The router is commented out in main.py until the migration is complete.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.django_setup import TelegramUser, Transaction, Transcription
from bot.filters import AdminFilter, SuperAdminFilter
from bot.keyboards.inline_keyboards import get_admin_keyboard
from bot.keyboards.main_menu import get_cancel_keyboard
from bot.states import AdminStates
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👨‍💼 Admin Panel", AdminFilter())
async def admin_panel(message: Message):
    """Show admin panel"""
    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\n" "Welcome to the admin control center.\n" "Select an action:",
        reply_markup=get_admin_keyboard(),
    )


@router.callback_query(F.data == "admin:stats", AdminFilter())
async def admin_stats(callback: CallbackQuery, session: AsyncSession):  # noqa: F821
    """Show bot statistics - DISABLED: Needs Django ORM migration"""
    # Get statistics
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # User stats
    total_users = await session.scalar(select(func.count(TelegramUser.id)))
    new_users_today = await session.scalar(
        select(func.count(TelegramUser.id)).where(func.date(TelegramUser.created_at) == today)
    )
    new_users_week = await session.scalar(
        select(func.count(TelegramUser.id)).where(func.date(TelegramUser.created_at) >= week_ago)
    )

    # Transaction stats
    total_revenue = (
            await session.scalar(
                select(func.sum(Transaction.amount)).where(
                    Transaction.type == "debit", Transaction.status == "completed"
                )
            )
            or 0
    )

    revenue_today = (
            await session.scalar(
                select(func.sum(Transaction.amount)).where(
                    Transaction.type == "debit",
                    Transaction.status == "completed",
                    func.date(Transaction.created_at) == today,
                )
            )
            or 0
    )

    # Transcription stats
    total_transcriptions = await session.scalar(select(func.count(Transcription.id)))
    transcriptions_today = await session.scalar(
        select(func.count(Transcription.id)).where(func.date(Transcription.created_at) == today)
    )

    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"<b>Users:</b>\n"
        f"Total: {total_users}\n"
        f"New today: {new_users_today}\n"
        f"New this week: {new_users_week}\n\n"
        f"<b>Revenue:</b>\n"
        f"Total: {total_revenue:,.2f} UZS\n"
        f"Today: {revenue_today:,.2f} UZS\n\n"
        f"<b>Transcriptions:</b>\n"
        f"Total: {total_transcriptions}\n"
        f"Today: {transcriptions_today}"
    )

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:users", AdminFilter())
async def admin_users(callback: CallbackQuery, state: FSMContext):
    """User management"""
    await state.set_state(AdminStates.searching_user)
    await callback.message.edit_text(
        "👥 <b>User Management</b>\n\n" "Send user's Telegram ID or @username to search:"
    )
    await callback.message.answer("Enter user ID or username:", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.searching_user, AdminFilter())
async def search_user(message: Message, state: FSMContext, session: AsyncSession):
    """Search for user"""
    search_query = message.text.strip()

    if search_query.startswith("@"):
        # Search by username
        username = search_query[1:]
        stmt = select(TelegramUser).where(TelegramUser.telegram_username == username)
    else:
        try:
            # Search by ID
            user_id = int(search_query)
            stmt = select(TelegramUser).where(TelegramUser.telegram_id == user_id)
        except ValueError:
            await message.answer("❌ Invalid user ID or username")
            return

    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found")
        return

    # Get user's wallet
    wallet = await user.get_wallet(session)

    # Get user statistics
    trans_count = await session.scalar(
        select(func.count(Transcription.id)).where(Transcription.user_id == user.id)
    )

    total_spent = (
            await session.scalar(
                select(func.sum(Transaction.amount)).where(
                    Transaction.user_id == user.id, Transaction.type == "debit"
                )
            )
            or 0
    )

    text = (
        f"👤 <b>User Information</b>\n\n"
        f"ID: {user.telegram_id}\n"
        f"Username: @{user.telegram_username}\n"
        f"Name: {user.first_name} {user.last_name or ''}\n"
        f"Language: {user.language_code}\n"
        f"Registered: {user.created_at.strftime('%Y-%m-%d')}\n\n"
        f"<b>Wallet:</b>\n"
        f"Balance: {wallet.balance:.2f} UZS\n"
        f"Total spent: {total_spent:.2f} UZS\n\n"
        f"<b>Activity:</b>\n"
        f"Transcriptions: {trans_count}\n"
        f"Last activity: {user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else 'Never'}"
    )

    await message.answer(text)
    await state.clear()


@router.callback_query(F.data == "admin:broadcast", SuperAdminFilter())
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast"""
    await state.set_state(AdminStates.entering_broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Broadcast Message</b>\n\n" "Send the message you want to broadcast to all users:"
    )
    await callback.message.answer("Enter broadcast message:", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.entering_broadcast_message, SuperAdminFilter())
async def broadcast_message(message: Message, state: FSMContext, session: AsyncSession):
    """Send broadcast to all users"""
    broadcast_text = message.text

    # Get all users
    stmt = select(TelegramUser.telegram_id)
    result = await session.execute(stmt)
    user_ids = [row[0] for row in result]

    # Send broadcast
    success = 0
    failed = 0

    status_msg = await message.answer(f"📤 Sending broadcast...\n" f"Progress: 0/{len(user_ids)}")

    for i, user_id in enumerate(user_ids):
        try:
            await message.bot.send_message(chat_id=user_id, text=broadcast_text)
            success += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1

        # Update progress every 10 users
        if (i + 1) % 10 == 0:
            await status_msg.edit_text(
                f"📤 Sending broadcast...\n"
                f"Progress: {i + 1}/{len(user_ids)}\n"
                f"Success: {success} | Failed: {failed}"
            )

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"Total: {len(user_ids)}\n"
        f"Success: {success}\n"
        f"Failed: {failed}"
    )

    await state.clear()


@router.callback_query(F.data == "admin:exit", AdminFilter())
async def exit_admin(callback: CallbackQuery):
    """Exit admin panel"""
    await callback.message.delete()
    await callback.answer("Exited admin panel")


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_ids


@router.message(Command("topup_user"), AdminFilter())
async def admin_topup_user(message: Message, user, session: AsyncSession):
    """Admin command to top up user balance.

    Usage: /topup_user <user_id> <amount> [description]
    Example: /topup_user 123456789 1000 "Bonus for testing"
    """

    # Parse command arguments
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❌ <b>Invalid format!</b>\n\n"
            "Usage: <code>/topup_user &lt;user_id&gt; &lt;amount&gt; [description]</code>\n\n"
            "Examples:\n"
            "• <code>/topup_user 123456789 1000</code>\n"
            "• <code>/topup_user 123456789 1000 Bonus for testing</code>"
        )
        return

    try:
        target_user_id = int(parts[1])
        amount = Decimal(parts[2])
        description = " ".join(parts[3:]) if len(parts) > 3 else "Admin top-up"

        # Validate amount
        if amount <= 0:
            await message.answer("❌ Amount must be positive!")
            return

        if amount > 1000000:
            await message.answer("❌ Amount too large! Maximum: 1,000,000 UZS")
            return

        # Find target user
        stmt = select(TelegramUser).where(TelegramUser.telegram_id == target_user_id)
        result = await session.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            await message.answer(f"❌ User with ID {target_user_id} not found!")
            return

        # Initialize wallet service and add balance
        wallet_service = WalletService(session)

        # Get current balance
        balance_info = await wallet_service.get_balance_info(target_user)
        old_balance = balance_info.current_balance

        # Add balance
        result = await wallet_service.add_balance(
            user=target_user,
            amount=amount,
            description=f"Admin top-up: {description}",
            reference_id=f"admin_topup_{message.message_id}",
        )

        if result.success:
            await session.commit()

            # Send success message to admin
            await message.answer(
                f"✅ <b>Balance Updated Successfully!</b>\n\n"
                f"👤 <b>User:</b> {target_user.first_name or 'N/A'} ({target_user_id})\n"
                f"💰 <b>Added:</b> +{amount:,.2f} UZS\n"
                f"💳 <b>Old Balance:</b> {old_balance:,.2f} UZS\n"
                f"💳 <b>New Balance:</b> {result.balance_after:,.2f} UZS\n"
                f"📝 <b>Description:</b> {description}\n"
                f"🆔 <b>Transaction ID:</b> {result.transaction_id}"
            )

            # Try to notify the user
            try:
                await message.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 <b>Balance Updated!</b>\n\n"
                         f"💰 <b>Added:</b> +{amount:,.2f} UZS\n"
                         f"💳 <b>New Balance:</b> {result.balance_after:,.2f} UZS\n"
                         f"📝 <b>Reason:</b> {description}\n\n"
                         f"Thank you! You can now use the transcription service.",
                )
                logger.info(f"Notified user {target_user_id} about balance top-up")
            except Exception as e:
                logger.warning(f"Could not notify user {target_user_id}: {e}")
                await message.answer(f"⚠️ Balance updated but couldn't notify user.")

        else:
            await message.answer(f"❌ <b>Error:</b> {result.error}")

    except ValueError as e:
        await message.answer("❌ Invalid user ID or amount format!")
    except Exception as e:
        logger.error(f"Error in admin_topup_user: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(Command("check_user"), AdminFilter())
async def admin_check_user(message: Message, user, session: AsyncSession):
    """Admin command to check user information.

    Usage: /check_user <user_id>
    Example: /check_user 123456789
    """

    # Parse command arguments
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "❌ <b>Invalid format!</b>\n\n"
            "Usage: <code>/check_user &lt;user_id&gt;</code>\n\n"
            "Example: <code>/check_user 123456789</code>"
        )
        return

    try:
        target_user_id = int(parts[1])

        # Find target user
        stmt = select(TelegramUser).where(TelegramUser.telegram_id == target_user_id)
        result = await session.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            await message.answer(f"❌ User with ID {target_user_id} not found!")
            return

        # Get wallet information
        wallet_service = WalletService(session)
        balance_info = await wallet_service.get_balance_info(target_user)

        # Get recent transactions
        recent_transactions = await wallet_service.get_transaction_history(target_user, limit=5)

        # Format user info
        user_info = (
            f"👤 <b>User Information</b>\n\n"
            f"🆔 <b>Telegram ID:</b> {target_user.telegram_id}\n"
            f"👤 <b>Name:</b> {target_user.first_name} {target_user.last_name or ''}\n"
            f"📧 <b>Username:</b> @{target_user.username or 'N/A'}\n"
            f"🌍 <b>Language:</b> {target_user.language_code}\n"
            f"📅 <b>Joined:</b> {target_user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"⏰ <b>Last Active:</b> {target_user.last_activity.strftime('%Y-%m-%d %H:%M') if target_user.last_activity else 'Never'}\n\n"
            f"💰 <b>Wallet Information</b>\n"
            f"💳 <b>Balance:</b> {balance_info.current_balance:,.2f} UZS\n"
            f"📈 <b>Total Added:</b> {balance_info.total_credited:,.2f} UZS\n"
            f"📉 <b>Total Spent:</b> {balance_info.total_debited:,.2f} UZS\n"
            f"🔢 <b>Transcriptions:</b> {target_user.total_transcriptions}\n\n"
        )

        if recent_transactions:
            user_info += f"📊 <b>Recent Transactions:</b>\n"
            for trans in recent_transactions[:3]:
                emoji = "💰" if trans.type == "credit" else "💸"
                sign = "+" if trans.type == "credit" else "-"
                user_info += f"   {emoji} {sign}{trans.amount:.2f} - {trans.description[:30]}...\n"
        else:
            user_info += "📊 <b>No transactions yet</b>"

        await message.answer(user_info)

    except ValueError:
        await message.answer("❌ Invalid user ID format!")
    except Exception as e:
        logger.error(f"Error in admin_check_user: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(Command("admin_help"), AdminFilter())
async def admin_help(message: Message, user):
    """Show admin help commands."""

    help_text = (
        f"🔧 <b>Admin Commands</b>\n\n"
        f"💰 <b>Balance Management:</b>\n"
        f"• <code>/topup_user &lt;user_id&gt; &lt;amount&gt; [description]</code>\n"
        f"   Add balance to user's wallet\n\n"
        f"👤 <b>User Management:</b>\n"
        f"• <code>/check_user &lt;user_id&gt;</code>\n"
        f"   View user information and balance\n\n"
        f"ℹ️ <b>Help:</b>\n"
        f"• <code>/admin_help</code>\n"
        f"   Show this help message\n\n"
        f"📋 <b>Examples:</b>\n"
        f"• <code>/topup_user 123456789 1000</code>\n"
        f"• <code>/topup_user 123456789 500 Welcome bonus</code>\n"
        f"• <code>/check_user 123456789</code>\n\n"
        f"👑 <b>Your admin ID:</b> {user.telegram_id}"
    )

    await message.answer(help_text)
