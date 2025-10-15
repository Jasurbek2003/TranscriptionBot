"""
History handlers - Currently disabled and needs refactoring to Django ORM.

This module uses SQLAlchemy-style queries that need to be converted to Django ORM.
The router is commented out in main.py until the migration is complete.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
import logging

from bot.keyboards.inline_keyboards import get_pagination_keyboard
from django_admin.apps.transcriptions.models import Transcription

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📊 History")
async def show_history(message: Message, session: AsyncSession, user):
    """Show transcription history"""
    await show_transcription_history(message, session, user, page=1)


async def show_transcription_history(
        message: Message,
        session: AsyncSession,
        user,
        page: int = 1,
        edit: bool = False
):
    """Show paginated transcription history"""
    per_page = 5
    offset = (page - 1) * per_page

    # Get total count
    count_stmt = select(func.count(Transcription.id)).where(
        Transcription.user_id == user.id
    )
    total_count = await session.scalar(count_stmt)

    if total_count == 0:
        text = "📜 <b>Transcription History</b>\n\nYou have no transcriptions yet."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    # Get transcriptions
    stmt = select(Transcription).where(
        Transcription.user_id == user.id
    ).order_by(
        desc(Transcription.created_at)
    ).limit(per_page).offset(offset)

    result = await session.execute(stmt)
    transcriptions = result.scalars().all()

    # Build message
    text = f"📜 <b>Transcription History</b>\n"
    text += f"Total: {total_count} | Page {page}/{(total_count + per_page - 1) // per_page}\n\n"

    for trans in transcriptions:
        duration_min = trans.duration_seconds // 60
        duration_sec = trans.duration_seconds % 60

        text += (
            f"📄 {trans.file_type.capitalize()} - {duration_min}:{duration_sec:02d}\n"
            f"   Cost: {trans.cost:.2f} UZS\n"
            f"   Date: {trans.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"   Status: {trans.status}\n\n"
        )

    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page

    # Send or edit message
    if edit:
        await message.edit_text(
            text,
            reply_markup=get_pagination_keyboard(page, total_pages, "trans_history")
        )
    else:
        await message.answer(
            text,
            reply_markup=get_pagination_keyboard(page, total_pages, "trans_history")
        )


@router.callback_query(F.data.startswith("trans_history:page:"))
async def history_pagination(
        callback: CallbackQuery,
        session: AsyncSession,
        user
):
    """Handle transcription history pagination"""
    page_str = callback.data.split(":")[2]

    if page_str == "current":
        await callback.answer()
        return

    page = int(page_str)
    await show_transcription_history(
        callback.message,
        session,
        user,
        page=page,
        edit=True
    )
    await callback.answer()