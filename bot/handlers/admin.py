from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging

from bot.filters import AdminFilter, SuperAdminFilter
from bot.states import AdminStates
from bot.keyboards.inline_keyboards import get_admin_keyboard
from bot.keyboards.main_menu import get_cancel_keyboard
from bot.config import settings
from django_admin.apps.users.models import TelegramUser
from django_admin.apps.transactions.models import Transaction
from django_admin.apps.transcriptions.models import Transcription

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👨‍💼 Admin Panel", AdminFilter())
async def admin_panel(message: Message):
    """Show admin panel"""
    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\n"
        "Welcome to the admin control center.\n"
        "Select an action:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin:stats", AdminFilter())
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    """Show bot statistics"""
    # Get statistics
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # User stats
    total_users = await session.scalar(
        select(func.count(TelegramUser.id))
    )
    new_users_today = await session.scalar(
        select(func.count(TelegramUser.id)).where(
            func.date(TelegramUser.created_at) == today
        )
    )
    new_users_week = await session.scalar(
        select(func.count(TelegramUser.id)).where(
            func.date(TelegramUser.created_at) >= week_ago
        )
    )

    # Transaction stats
    total_revenue = await session.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.type == "debit",
            Transaction.status == "completed"
        )
    ) or 0

    revenue_today = await session.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.type == "debit",
            Transaction.status == "completed",
            func.date(Transaction.created_at) == today
        )
    ) or 0

    # Transcription stats
    total_transcriptions = await session.scalar(
        select(func.count(Transcription.id))
    )
    transcriptions_today = await session.scalar(
        select(func.count(Transcription.id)).where(
            func.date(Transcription.created_at) == today
        )
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
        "👥 <b>User Management</b>\n\n"
        "Send user's Telegram ID or @username to search:"
    )
    await callback.message.answer(
        "Enter user ID or username:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminStates.searching_user, AdminFilter())
async def search_user(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    """Search for user"""
    search_query = message.text.strip()

    if search_query.startswith("@"):
        # Search by username
        username = search_query[1:]
        stmt = select(TelegramUser).where(
            TelegramUser.telegram_username == username
        )
    else:
        try:
            # Search by ID
            user_id = int(search_query)
            stmt = select(TelegramUser).where(
                TelegramUser.telegram_id == user_id
            )
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
        select(func.count(Transcription.id)).where(
            Transcription.user_id == user.id
        )
    )

    total_spent = await session.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == "debit"
        )
    ) or 0

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
        "📢 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast to all users:"
    )
    await callback.message.answer(
        "Enter broadcast message:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminStates.entering_broadcast_message, SuperAdminFilter())
async def broadcast_message(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    """Send broadcast to all users"""
    broadcast_text = message.text

    # Get all users
    stmt = select(TelegramUser.telegram_id)
    result = await session.execute(stmt)
    user_ids = [row[0] for row in result]

    # Send broadcast
    success = 0
    failed = 0

    status_msg = await message.answer(
        f"📤 Sending broadcast...\n"
        f"Progress: 0/{len(user_ids)}"
    )

    for i, user_id in enumerate(user_ids):
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=broadcast_text
            )
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
