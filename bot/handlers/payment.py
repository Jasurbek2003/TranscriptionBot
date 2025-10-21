"""Payment handlers with Click and Payme integration using Django ORM."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from decimal import Decimal
import logging
import uuid
from asgiref.sync import sync_to_async

from bot.states import PaymentStates
from bot.keyboards.payment_keyboards import (
    get_payment_methods_keyboard,
    get_amount_keyboard,
    get_payment_confirmation_keyboard
)
from bot.keyboards.main_menu import get_cancel_keyboard
from bot.config import settings
from bot.django_setup import Transaction, Wallet
from services.payment.payme_service import PaymeService
from services.payment.click_service import ClickService
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text.in_(["/topup", "💳 Top Up", "💳 Add Money"]))
async def start_topup(message: Message, state: FSMContext):
    """Start top-up process with Click and Payme payment methods"""
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

    print("Selected payment method:", method)

    # Save payment method
    await state.update_data(payment_method=method)
    await state.set_state(PaymentStates.entering_amount)

    # Show amount selection
    await callback.message.edit_text(
        f"💰 <b>Enter Amount</b>\n\n"
        f"Payment method: {method.capitalize()}\n"
        f"Minimum: {settings.pricing.min_payment_amount:,.0f} UZS\n"
        f"Maximum: {settings.pricing.max_payment_amount:,.0f} UZS\n\n"
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
            f"Minimum: {settings.pricing.min_payment_amount:,.0f} UZS\n"
            f"Maximum: {settings.pricing.max_payment_amount:,.0f} UZS"
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
    if amount < settings.pricing.min_payment_amount:
        await callback.answer(
            f"Minimum amount is {settings.pricing.min_payment_amount:,.0f} UZS",
            show_alert=True
        )
        return

    if amount > settings.pricing.max_payment_amount:
        await callback.answer(
            f"Maximum amount is {settings.pricing.max_payment_amount:,.0f} UZS",
            show_alert=True
        )
        return

    # Process payment
    await process_payment(callback.message, state, user, amount)
    await callback.answer()


@router.message(
    PaymentStates.entering_amount,
    F.text.regexp(r"^\d+(\.\d{1,2})?$")
)
async def handle_custom_amount(
        message: Message,
        state: FSMContext,
        user
):
    """Handle custom amount input"""
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("❌ Please enter a valid number")
        return

    # Validate amount
    if amount < settings.pricing.min_payment_amount:
        await message.answer(
            f"❌ Minimum amount is {settings.pricing.min_payment_amount:,.0f} UZS"
        )
        return

    if amount > settings.pricing.max_payment_amount:
        await message.answer(
            f"❌ Maximum amount is {settings.pricing.max_payment_amount:,.0f} UZS"
        )
        return

    await process_payment(message, state, user, amount)


async def process_payment(
        message: Message,
        state: FSMContext,
        user,
        amount: float
):
    """Process payment with selected method"""
    data = await state.get_data()
    payment_method = data.get("payment_method")

    # Get or create wallet
    wallet_service = WalletService()
    wallet = await wallet_service.get_or_create_wallet(user)

    # Generate transaction ID
    transaction_id = str(uuid.uuid4())

    # Create pending transaction
    @sync_to_async
    def create_transaction():
        return Transaction.objects.create(
            user=user,
            wallet=wallet,
            type="credit",
            amount=Decimal(str(amount)),
            balance_before=wallet.balance,
            balance_after=wallet.balance,  # Will be updated when payment is confirmed
            payment_method=payment_method,
            status="pending",
            reference_id=transaction_id,
            description=f"Top up via {payment_method.capitalize()}"
        )

    transaction = await create_transaction()

    # Save transaction data
    await state.update_data(
        amount=amount,
        transaction_id=transaction_id
    )
    await state.set_state(PaymentStates.waiting_for_payment)

    # Initialize payment services
    if payment_method == "payme":
        payment_service = PaymeService(
            merchant_id=settings.payment.payme_merchant_id,
            secret_key=settings.payment.payme_secret_key,
            test_mode=settings.payment.payme_test_mode
        )
        payment_url = payment_service.create_payment_link(
            amount=amount,
            order_id=transaction_id,
            return_url=None  # Optional: add return URL if needed
        )
    elif payment_method == "click":
        payment_service = ClickService(
            merchant_id=settings.payment.click_merchant_id,
            service_id=settings.payment.click_service_id,
            secret_key=settings.payment.click_secret_key,
            test_mode=settings.payment.click_test_mode
        )
        payment_url = payment_service.create_payment_link(
            amount=amount,
            order_id=transaction_id,
            return_url=None  # Optional: add return URL if needed
        )
    else:
        await message.answer("❌ Invalid payment method")
        await state.clear()
        return

    # Create payment button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay Now", url=payment_url)],
        [InlineKeyboardButton(text="✅ I have paid", callback_data=f"confirm_payment:{transaction_id}")],
        [InlineKeyboardButton(text="❌ Cancel payment", callback_data=f"cancel_payment:{transaction_id}")]
    ])

    # Send payment instructions
    await message.answer(
        f"💳 <b>Payment Instructions</b>\n\n"
        f"💰 Amount: <b>{amount:,.2f} UZS</b>\n"
        f"💳 Method: <b>{payment_method.capitalize()}</b>\n"
        f"🆔 Transaction ID: <code>{transaction_id}</code>\n\n"
        f"📌 <b>Steps to complete payment:</b>\n"
        f"1. Click '<b>Pay Now</b>' button below\n"
        f"2. Complete payment on {payment_method.capitalize()} page\n"
        f"3. Return here and click '<b>I have paid</b>'\n\n"
        f"⚠️ <i>Payment will be automatically verified within seconds</i>",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment(
        callback: CallbackQuery,
        state: FSMContext,
        user,
        wallet
):
    """Handle payment confirmation - check if payment was received"""
    transaction_id = callback.data.split(":")[1]

    # Get transaction from database
    @sync_to_async
    def get_transaction():
        return Transaction.objects.filter(
            reference_id=transaction_id,
            user_id=user.id
        ).first()

    transaction = await get_transaction()

    if not transaction:
        await callback.answer("❌ Transaction not found!", show_alert=True)
        return

    # Check if already completed
    if transaction.status == "completed":
        await callback.answer("✅ This payment is already completed!", show_alert=True)
        return

    # NOTE: Click and Payme use webhooks for actual verification
    # This button check is just for user experience
    # In production, you should query your backend to see if webhook was received

    await callback.answer(
        "⏳ Checking payment status...\n\n"
        "If you've completed the payment, it will be verified automatically within 1-2 minutes.\n\n"
        "The payment gateway will send us a confirmation.",
        show_alert=True
    )

    # Check transaction status again (in case webhook already updated it)
    @sync_to_async
    def check_transaction_status():
        transaction.refresh_from_db()
        return transaction.status

    current_status = await check_transaction_status()

    if current_status == "completed":
        # Refresh wallet
        @sync_to_async
        def get_wallet():
            wallet_obj = Wallet.objects.get(user=user)
            return wallet_obj.balance

        new_balance = await get_wallet()

        # Clear state
        await state.clear()

        # Send success message
        await callback.message.edit_text(
            f"✅ <b>Payment Verified!</b>\n\n"
            f"💰 Amount: <b>{transaction.amount:,.2f} UZS</b>\n"
            f"💳 New Balance: <b>{new_balance:,.2f} UZS</b>\n"
            f"🆔 Transaction ID: <code>{transaction_id}</code>\n\n"
            f"Thank you for your payment! 🎉"
        )

        logger.info(
            f"Payment confirmed: user={user.telegram_id}, "
            f"amount={transaction.amount}, ref={transaction_id}"
        )
    else:
        await callback.message.edit_text(
            f"⏳ <b>Payment Pending</b>\n\n"
            f"💰 Amount: <b>{transaction.amount:,.2f} UZS</b>\n"
            f"🆔 Transaction ID: <code>{transaction_id}</code>\n\n"
            f"Your payment is being processed. You will receive a confirmation message once it's verified.\n\n"
            f"⚠️ <i>This usually takes 1-2 minutes</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Check Again", callback_data=f"confirm_payment:{transaction_id}")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_payment:{transaction_id}")]
            ])
        )


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment(
        callback: CallbackQuery,
        state: FSMContext,
        user
):
    """Handle payment cancellation"""
    transaction_id = callback.data.split(":")[1]

    # Update transaction status
    @sync_to_async
    def cancel_transaction():
        transaction = Transaction.objects.filter(
            reference_id=transaction_id,
            user_id=user.id
        ).first()

        if transaction and transaction.status == "pending":
            transaction.cancel()
            return True
        return False

    was_cancelled = await cancel_transaction()

    await state.clear()

    if was_cancelled:
        await callback.message.edit_text(
            "❌ <b>Payment Cancelled</b>\n\n"
            "The payment has been cancelled successfully.\n"
            "You can initiate a new payment anytime using /topup command."
        )
    else:
        await callback.message.edit_text("❌ Payment cancelled or not found")

    await callback.answer()
