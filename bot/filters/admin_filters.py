from typing import Union, List
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from bot.config import settings


class AdminFilter(Filter):
    """Filter for admin users"""

    def __init__(self, admin_ids: List[int] = None):
        self.admin_ids = admin_ids or settings.admin_ids

    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        user_id = obj.from_user.id if obj.from_user else None
        return user_id in self.admin_ids if user_id else False


class SuperAdminFilter(Filter):
    """Filter for super admin (first admin in list)"""

    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if not settings.admin_ids:
            return False

        user_id = obj.from_user.id if obj.from_user else None
        return user_id == settings.admin_ids[0] if user_id else False