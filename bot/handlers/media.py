from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio
import logging

from bot.filters import AudioFilter, VideoFilter, FileSizeFilter
from bot.states import TranscriptionStates
from bot.keyboards.inline_keyboards import get_transcription_keyboard, get_rating_keyboard
from bot.config import settings
from services.transcription.gemini_service import GeminiTranscriptionService
from services.payment.wallet_service import WalletService
from django_admin.apps.transcriptions.models import Transcription
from django_admin.apps.transactions.models import Transaction

logger = logging.getLogger(__name__)

router = Router()

# Initialize services
transcription_service = GeminiTranscriptionService(settings.GEMINI_API_KEY)


@router.message(F.text == "📎 Send Media")
async def request_media(message: Message, state: FSMContext):
    """Request user to send media"""
    await state.set_state(TranscriptionStates.waiting_for_media)

    await message.answer(
        "📎 <b>Send Media File</b>\n\n"
        "Please send an audio or video file for transcription.\n\n"
        "Supported formats:\n"
        "• Audio: MP3, WAV, OGG, M4A\n"
        "• Video: MP4, AVI, MOV, MKV\n\n"
        f"Maximum duration:\n"
        f"• Audio: {settings.MAX_AUDIO_DURATION_SECONDS // 60} minutes\n"
        f"• Video: {settings.MAX_VIDEO_DURATION_SECONDS // 60} minutes\n"
        f"• File size: {settings.MAX_FILE_SIZE_MB} MB"
    )


@router.message(
    TranscriptionStates.waiting_for_media,
    AudioFilter(),
    FileSizeFilter()
)
async def process_audio(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet,
        media_type: str,
        duration: int,
        file_id: str,
        file_size: int
):
    """Process audio file"""
    await process_media_file(
        message, state, session, user, wallet,
        media_type, duration, file_id, file_size
    )


@router.message(
    TranscriptionStates.waiting_for_media,
    VideoFilter(),
    FileSizeFilter()
)
async def process_video(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet,
        media_type: str,
        duration: int,
        file_id: str,
        file_size: int
):
    """Process video file"""
    await process_media_file(
        message, state, session, user, wallet,
        media_type, duration, file_id, file_size
    )


async def process_media_file(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet,
        media_type: str,
        duration: int,
        file_id: str,
        file_size: int
):
    """Common media processing logic"""

    # Clear state
    await state.clear()

    # Send processing message
    processing_msg = await message.answer(
        "⏳ <b>Processing your file...</b>\n\n"
        "This may take a few moments depending on the file size."
    )

    try:
        # Calculate cost
        duration_minutes = (duration + 59) // 60  # Round up
        price_per_minute = (
            settings.VIDEO_PRICE_PER_MIN
            if media_type == "video"
            else settings.AUDIO_PRICE_PER_MIN
        )
        total_cost = duration_minutes * price_per_minute

        # Check balance again
        if wallet.balance < total_cost:
            await processing_msg.edit_text(
                f"❌ <b>Insufficient balance</b>\n\n"
                f"Cost: {total_cost:.2f} UZS\n"
                f"Your balance: {wallet.balance:.2f} UZS\n\n"
                f"Please top up your balance to continue."
            )
            return

        # Update processing message
        await processing_msg.edit_text(
            f"📊 <b>File Information</b>\n\n"
            f"Type: {media_type.capitalize()}\n"
            f"Duration: {duration // 60}:{duration % 60:02d}\n"
            f"Size: {file_size / 1024 / 1024:.2f} MB\n"
            f"Cost: {total_cost:.2f} UZS\n\n"
            f"⏳ Starting transcription..."
        )

        # Download file
        bot = message.bot
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)

        # Start transcription
        transcription_text = await transcription_service.transcribe_from_bytes(
            file_bytes,
            media_type,
            duration
        )

        if not transcription_text:
            await processing_msg.edit_text(
                "❌ <b>Transcription Failed</b>\n\n"
                "Sorry, we couldn't transcribe your file. "
                "Your balance has not been charged.\n\n"
                "Please try again with a different file."
            )
            return

        # Deduct from wallet
        wallet_service = WalletService(session)
        success = await wallet_service.deduct_balance(
            user_id=user.id,
            amount=total_cost,
            description=f"Transcription of {media_type}"
        )

        if not success:
            await processing_msg.edit_text(
                "❌ <b>Payment Error</b>\n\n"
                "There was an error processing the payment. "
                "Please try again later."
            )
            return

        # Save transcription to database
        transcription = Transcription(
            user_id=user.id,
            file_telegram_id=file_id,
            file_type=media_type,
            duration_seconds=duration,
            transcription_text=transcription_text,
            cost=total_cost,
            status="completed"
        )
        session.add(transcription)

        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            type="debit",
            amount=total_cost,
            description=f"Transcription of {media_type} ({duration // 60}:{duration % 60:02d})",
            status="completed",
            reference_id=f"trans_{transcription.id}"
        )
        session.add(transaction)

        await session.commit()

        # Update wallet balance in memory
        wallet.balance -= total_cost

        # Send transcription file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcription_{timestamp}.txt"

        await message.answer_document(
            BufferedInputFile(
                transcription_text.encode('utf-8'),
                filename=filename
            ),
            caption=(
                f"✅ <b>Transcription Complete!</b>\n\n"
                f"📁 File: {filename}\n"
                f"⏱ Duration: {duration // 60}:{duration % 60:02d}\n"
                f"💰 Cost: {total_cost:.2f} UZS\n"
                f"💳 New Balance: {wallet.balance:.2f} UZS"
            ),
            reply_markup=get_transcription_keyboard(str(transcription.id))
        )

        # Delete processing message
        await processing_msg.delete()

        # Ask for rating
        await asyncio.sleep(2)
        await message.answer(
            "⭐ <b>Rate this transcription</b>\n\n"
            "How satisfied are you with the quality?",
            reply_markup=get_rating_keyboard()
        )

        logger.info(
            f"Transcription completed for user {user.telegram_id}: "
            f"{media_type}, {duration}s, cost: {total_cost}"
        )

    except Exception as e:
        logger.error(f"Error processing media: {e}", exc_info=True)
        await processing_msg.edit_text(
            "❌ <b>Processing Error</b>\n\n"
            "An unexpected error occurred while processing your file. "
            "Your balance has not been charged.\n\n"
            "Please try again later or contact support if the issue persists."
        )


@router.callback_query(F.data.startswith("rating:"))
async def handle_rating(
        callback: CallbackQuery,
        session: AsyncSession,
        user
):
    """Handle transcription rating"""
    rating_value = callback.data.split(":")[1]

    if rating_value == "skip":
        await callback.message.edit_text(
            "Thank you for using our service! 😊"
        )
    else:
        rating = int(rating_value)
        # TODO: Save rating to database

        await callback.message.edit_text(
            f"Thank you for your feedback! {'⭐' * rating}\n\n"
            f"Your opinion helps us improve our service."
        )

    await callback.answer()


@router.callback_query(F.data.startswith("download:"))
async def download_transcription(
        callback: CallbackQuery,
        session: AsyncSession,
        user
):
    """Handle transcription download request"""
    transcription_id = callback.data.split(":")[1]

    # Get transcription from database
    transcription = await session.get(Transcription, int(transcription_id))

    if not transcription or transcription.user_id != user.id:
        await callback.answer("Transcription not found!", show_alert=True)
        return

    # Send file
    timestamp = transcription.created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"transcription_{timestamp}.txt"

    await callback.message.answer_document(
        BufferedInputFile(
            transcription.transcription_text.encode('utf-8'),
            filename=filename
        ),
        caption=f"📄 Your transcription: {filename}"
    )

    await callback.answer("File sent!")


# Handle media sent without command
@router.message(AudioFilter(), FileSizeFilter())
@router.message(VideoFilter(), FileSizeFilter())
async def handle_direct_media(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user,
        wallet,
        media_type: str,
        duration: int,
        file_id: str,
        file_size: int
):
    """Handle media sent directly without using menu"""
    await process_media_file(
        message, state, session, user, wallet,
        media_type, duration, file_id, file_size
    )