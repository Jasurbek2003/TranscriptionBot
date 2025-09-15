from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """Payment process states"""

    # Top-up process
    choosing_payment_method = State()
    entering_amount = State()
    confirming_payment = State()
    processing_payment = State()

    # Withdrawal process (if needed)
    entering_withdrawal_amount = State()
    entering_card_number = State()
    confirming_withdrawal = State()

    # Payment verification
    waiting_for_payment = State()
    payment_verification = State()
