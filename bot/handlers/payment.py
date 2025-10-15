"""
Payment handlers - Currently disabled and needs refactoring to Django ORM.

This module uses SQLAlchemy-style queries that need to be converted to Django ORM.
The router is commented out in main.py until the migration is complete.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from decimal import Decimal
import logging
import uuid

from bot.states import PaymentStates
from bot.keyboards.payment_keyboards import (
    get_payment_methods_keyboard,
    get_amount_keyboard,
    get_payment_confirmation_keyboard
)
from bot.keyboards.main_menu import get_cancel_keyboard
from bot.config import settings
from services.payment.payme_service import PaymeService
from services.payment.click_service import ClickService
# from services.payment.wallet_service import WalletService
# from django_admin.apps.transactions.models import Transaction

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "💳 Top Up")
async def start_topup(message: Message, state: FSMContext):
    """Start top-up process"""
    await state.set_state(PaymentStates.choosing_payment_method)

    await message.answer(
        "💳 <b>Top Up Balance</b>\n\n"
        "Choose your payment method:",
        reply_markup=get_payment_methods_keyboard()
    )


@router.callback_query(
    PaymentStates.choosing_payment_method,
    F.data.startswith("payment:")
)
async def choose_payment_method(
        callback: CallbackQuery,
        state: FSMContext
):
    """Handle payment method selection"""
    method = callback.data.split(":")[1]

    if method == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Payment cancelled")
        await callback.answer()
        return

    # Save payment method
    await state.update_data(payment_method=method)
    await state.set_state(PaymentStates.entering_amount)

    # Show amount selection
    await callback.message.edit_text(
        f"💰 <b>Enter Amount</b>\n\n"
        f"Payment method: {method.capitalize()}\n"
        f"Minimum: {settings.MIN_PAYMENT_AMOUNT:,.0f} UZS\n"
        f"Maximum: {settings.MAX_PAYMENT_AMOUNT:,.0f} UZS\n\n"
        f"Select or enter custom amount:",
        reply_markup=get_amount_keyboard()
    )
    await callback.answer()


@router.callback_query(
    PaymentStates.entering_amount,
    F.data.startswith("amount:")
)
async def handle_amount_selection(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        user
):
    """Handle amount selection"""
    amount_str = callback.data.split(":")[1]

    if amount_str == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Payment cancelled")
        await callback.answer()
        return

    if amount_str == "custom":
        await callback.message.edit_text(
            "💵 Please enter the amount in UZS:\n\n"
            f"Minimum: {settings.MIN_PAYMENT_AMOUNT:,.0f} UZS\n"
            f"Maximum: {settings.MAX_PAYMENT_AMOUNT:,.0f} UZS"
        )
        await callback.message.answer(
            "Enter amount:",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()
        return

    try:
        amount = float(amount_str)
    except ValueError:
        await callback.answer("Invalid amount!", show_alert=True)
        return

    # Validate amount
    if amount < settings.MIN_PAYMENT_AMOUNT:
        await callback.answer(
            f"Minimum amount is {settings.MIN_PAYMENT_AMOUNT:,.0f} UZS",
            show_alert=True
        )
        return

    if amount > settings.MAX_PAYMENT_AMOUNT:
        await callback.answer(
            f"Maximum amount is {settings.MAX_PAYMENT_AMOUNT:,.0f} UZS",
            show_alert=True
        )
        return

    # Process payment
    await process_payment(callback.message, state, session, user, amount)
    await callback.answer()


@router.message(
    PaymentStates.entering_amount,
    F.text.regexp(r"^\d+(\.\d{1,2})?$")
)
async def handle_custom_amount(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user
):
    """Handle custom amount input"""
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("❌ Please enter a valid number")
        return

    # Validate amount
    if amount < settings.MIN_PAYMENT_AMOUNT:
        await message.answer(
            f"❌ Minimum amount is {settings.MIN_PAYMENT_AMOUNT:,.0f} UZS"
        )
        return

    if amount > settings.MAX_PAYMENT_AMOUNT:
        await message.answer(
            f"❌ Maximum amount is {settings.MAX_PAYMENT_AMOUNT:,.0f} UZS"
        )
        return

    await process_payment(message, state, session, user, amount)


async def process_payment(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        amount: float
):
    """Process payment with selected method"""
    data = await state.get_data()
    payment_method = data.get("payment_method")

    # Get or create wallet
    from services.wallet_service import WalletService
    wallet_service = WalletService(session)
    wallet = await wallet_service.get_or_create_wallet(user)

    # Generate transaction ID
    transaction_id = str(uuid.uuid4())

    # Create pending transaction
    transaction = Transaction(
        user_id=user.id,
        wallet_id=wallet.id,
        type="credit",
        amount=Decimal(str(amount)),
        balance_before=wallet.balance,
        balance_after=wallet.balance,  # Will be updated when payment is confirmed
        payment_method=payment_method,
        status="pending",
        reference_id=transaction_id,
        description=f"Top up via {payment_method.capitalize()}"
    )
    session.add(transaction)
    await session.commit()

    # Save transaction data
    await state.update_data(
        amount=amount,
        transaction_id=transaction_id
    )
    await state.set_state(PaymentStates.waiting_for_payment)

    # Generate payment link based on method
    if payment_method == "payme":
        payment_service = PaymeService()
        payment_url = await payment_service.create_payment_link(
            amount=amount,
            order_id=transaction_id,
            user_id=str(user.telegram_id)
        )
    elif payment_method == "click":
        payment_service = ClickService()
        payment_url = await payment_service.create_payment_link(
            amount=amount,
            order_id=transaction_id,
            user_id=str(user.telegram_id)
        )
    else:
        await message.answer("❌ Invalid payment method")
        await state.clear()
        return

    # Send payment instructions
    await message.answer(
        f"💳 <b>Payment Instructions</b>\n\n"
        f"Amount: {amount:,.2f} UZS\n"
        f"Method: {payment_method.capitalize()}\n"
        f"Transaction ID: <code>{transaction_id}</code>\n\n"
        f"Please complete the payment using the link below:\n"
        f"{payment_url}\n\n"
        f"After payment, click 'I have paid' button.",
        reply_markup=get_payment_confirmation_keyboard(
            amount, payment_method, transaction_id
        ),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet
):
    """Handle payment confirmation"""
    transaction_id = callback.data.split(":")[1]

    # Get transaction from database
    transaction = await session.query(Transaction).filter_by(
        reference_id=transaction_id,
        user_id=user.id
    ).first()

    if not transaction:
        await callback.answer("Transaction not found!", show_alert=True)
        return

    # Check payment status with payment provider
    data = await state.get_data()
    payment_method = data.get("payment_method")

    if payment_method == "payme":
        payment_service = PaymeService()
        is_paid = await payment_service.check_payment_status(transaction_id)
    elif payment_method == "click":
        payment_service = ClickService()
        is_paid = await payment_service.check_payment_status(transaction_id)
    else:
        is_paid = False

    if is_paid:
        # Update transaction status
        transaction.status = "completed"

        # Update wallet balance
        wallet_service = WalletService(session)
        await wallet_service.add_balance(
            user_id=user.id,
            amount=transaction.amount,
            description=f"Top up via {payment_method.capitalize()}"
        )

        await session.commit()

        # Clear state
        await state.clear()

        # Update wallet in memory
        wallet.balance += transaction.amount

        # Send success message
        await callback.message.edit_text(
            f"✅ <b>Payment Successful!</b>\n\n"
            f"Amount: {transaction.amount:,.2f} UZS\n"
            f"New Balance: {wallet.balance:,.2f} UZS\n"
            f"Transaction ID: <code>{transaction_id}</code>\n\n"
            f"Thank you for your payment!"
        )

        logger.info(
            f"Payment completed: user={user.telegram_id}, "
            f"amount={transaction.amount}, method={payment_method}"
        )
    else:
        await callback.answer(
            "⏳ Payment not yet received. Please complete the payment and try again.",
            show_alert=True
        )


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        user
):
    """Handle payment cancellation"""
    transaction_id = callback.data.split(":")[1]

    # Update transaction status
    transaction = await session.query(Transaction).filter_by(
        reference_id=transaction_id,
        user_id=user.id
    ).first()

    if transaction and transaction.status == "pending":
        transaction.status = "cancelled"
        await session.commit()

    await state.clear()
    await callback.message.edit_text("❌ Payment cancelled")
    await callback.answer()


# bot/handlers/wallet.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import logging

from bot.keyboards.inline_keyboards import get_balance_keyboard, get_pagination_keyboard
from django_admin.apps.transactions.models import Transaction

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "💰 My Balance")
async def show_balance(message: Message, wallet):
    """Show user balance"""
    await message.answer(
        f"💰 <b>Your Balance</b>\n\n"
        f"Current balance: {wallet.balance:,.2f} UZS\n"
        f"Currency: {wallet.currency}\n\n"
        f"Use the buttons below to manage your balance:",
        reply_markup=get_balance_keyboard()
    )


@router.callback_query(F.data == "action:topup")
async def topup_callback(callback: CallbackQuery, state: FSMContext):
    """Handle top-up callback"""
    from bot.handlers.payment import start_topup
    await callback.message.delete()
    await start_topup(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "action:history")
async def history_callback(callback: CallbackQuery, session: AsyncSession, user):
    """Show transaction history"""
    await show_transaction_history(callback.message, session, user, page=1)
    await callback.answer()


async def show_transaction_history(
        message: Message,
        session: AsyncSession,
        user,
        page: int = 1,
        edit: bool = False
):
    """Show paginated transaction history"""
    # Configuration
    per_page = 5
    offset = (page - 1) * per_page

    # Get total count
    count_stmt = select(func.count(Transaction.id)).where(
        Transaction.user_id == user.id
    )
    total_count = await session.scalar(count_stmt)

    if total_count == 0:
        text = "📊 <b>Transaction History</b>\n\nYou have no transactions yet."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    # Get transactions
    stmt = select(Transaction).where(
        Transaction.user_id == user.id
    ).order_by(
        desc(Transaction.created_at)
    ).limit(per_page).offset(offset)

    result = await session.execute(stmt)
    transactions = result.scalars().all()

    # Build message
    text = f"📊 <b>Transaction History</b>\n"
    text += f"Page {page}/{(total_count + per_page - 1) // per_page}\n\n"

    for trans in transactions:
        emoji = "➕" if trans.type == "credit" else "➖"
        status_emoji = {
            "completed": "✅",
            "pending": "⏳",
            "failed": "❌",
            "cancelled": "🚫"
        }.get(trans.status, "❓")

        text += (
            f"{emoji} {trans.amount:,.2f} UZS {status_emoji}\n"
            f"   {trans.description}\n"
            f"   {trans.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page

    # Send or edit message
    if edit:
        await message.edit_text(
            text,
            reply_markup=get_pagination_keyboard(page, total_pages, "history")
        )
    else:
        await message.answer(
            text,
            reply_markup=get_pagination_keyboard(page, total_pages, "history")
        )


@router.callback_query(F.data.startswith("history:page:"))
async def history_pagination(
        callback: CallbackQuery,
        session: AsyncSession,
        user
):
    """Handle history pagination"""
    page_str = callback.data.split(":")[2]

    if page_str == "current":
        await callback.answer()
        return

    page = int(page_str)
    await show_transaction_history(
        callback.message,
        session,
        user,
        page=page,
        edit=True
    )
    await callback.answer()
