from typing import Union

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message


class PrivateChatFilter(Filter):
    """Filter for private chat messages"""

    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if isinstance(obj, Message):
            return obj.chat.type == "private"
        elif isinstance(obj, CallbackQuery):
            return obj.message.chat.type == "private" if obj.message else False
        return False


class GroupChatFilter(Filter):
    """Filter for group chat messages"""

    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if isinstance(obj, Message):
            return obj.chat.type in ["group", "supergroup"]
        elif isinstance(obj, CallbackQuery):
            return obj.message.chat.type in ["group", "supergroup"] if obj.message else False
        return False
