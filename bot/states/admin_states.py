from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Admin panel states"""

    # Broadcast
    entering_broadcast_message = State()
    confirming_broadcast = State()

    # User management
    searching_user = State()
    editing_user_balance = State()
    blocking_user = State()

    # Settings
    updating_prices = State()
    updating_limits = State()

    # Statistics
    selecting_date_range = State()
    generating_report = State()

    # Maintenance
    entering_maintenance_message = State()
    scheduling_maintenance = State()
