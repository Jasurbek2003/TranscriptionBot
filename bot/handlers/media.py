from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
from decimal import Decimal
import asyncio
import logging
from asgiref.sync import sync_to_async

from bot.filters import AudioFilter, VideoFilter, FileSizeFilter
from bot.states import TranscriptionStates
from bot.keyboards.inline_keyboards import get_transcription_keyboard, get_rating_keyboard
from bot.config import settings
from bot.django_setup import Transcription
from services.transcription.gemini_service import GeminiTranscriptionService
from services.wallet_service import WalletService
from services.auth_service import AuthService

# Constants
TELEGRAM_STANDARD_API_FILE_LIMIT = 20 * 1024 * 1024  # 20MB for standard API

logger = logging.getLogger(__name__)

router = Router()

# Initialize services
transcription_service = GeminiTranscriptionService(settings.ai.gemini_api_key)


@router.message(F.text == "📎 Send Media")
async def request_media(message: Message, state: FSMContext):
    """Request user to send media"""
    await state.set_state(TranscriptionStates.waiting_for_media)

    # Determine max file size based on API server type
    max_file_mb = settings.max_downloadable_file_size / 1024 / 1024
    api_note = "" if settings.bot_api_server else "\n\n⚠️ Standard API limit: 20 MB"

    await message.answer(
        "📎 <b>Send Media File</b>\n\n"
        "Please send an audio or video file for transcription.\n\n"
        "Supported formats:\n"
        "• Audio: MP3, WAV, OGG, M4A\n"
        "• Video: MP4, AVI, MOV, MKV\n\n"
        f"Maximum duration:\n"
        f"• Audio: {settings.ai.max_audio_duration_seconds // 60} minutes\n"
        f"• Video: {settings.ai.max_video_duration_seconds // 60} minutes\n"
        f"• File size: {max_file_mb:.0f} MB{api_note}"
    )


@router.message(
    TranscriptionStates.waiting_for_media,
    AudioFilter()
)
async def process_audio(
        message: Message,
        state: FSMContext,
        user,
        wallet
):
    """Process audio file"""
    if message.audio:
        media_type = "audio"
        duration = message.audio.duration
        file_id = message.audio.file_id
        file_size = message.audio.file_size
    elif message.voice:
        media_type = "audio"
        duration = message.voice.duration
        file_id = message.voice.file_id
        file_size = message.voice.file_size
    else:
        await message.answer("❌ Audio file not found.")
        return

    await process_media_file(message, state, user, wallet, media_type, duration, file_id, file_size)


@router.message(
    TranscriptionStates.waiting_for_media,
    VideoFilter()
)
async def process_video(
        message: Message,
        state: FSMContext,
        user,
        wallet
):
    """Process video file"""
    if message.video:
        media_type = "video"
        duration = message.video.duration
        file_id = message.video.file_id
        file_size = message.video.file_size
    else:
        await message.answer("❌ Video file not found.")
        return

    await process_media_file(message, state, user, wallet, media_type, duration, file_id, file_size)


async def process_media_file(
        message: Message,
        state: FSMContext,
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

    # Check if file is larger than 20MB
    logger.info(f"File size check: {file_size} bytes, limit: {TELEGRAM_STANDARD_API_FILE_LIMIT} bytes")
    if file_size > TELEGRAM_STANDARD_API_FILE_LIMIT:
        logger.info(f"File is large, generating auth token for user {user.id}")
        # Generate one-time sign-in URL for large files
        auth_service = AuthService()
        token = await auth_service.generate_token(
            user=user,
            purpose="large_file_upload",
            expires_in_hours=24  # Token valid for 24 hours
        )
        logger.info(f"Token generated: {token.token}")

        # Get web app URL from settings (default to localhost for development)
        web_app_url = settings.web_app_url if hasattr(settings, 'web_app_url') else "http://127.0.0.1:8000"
        sign_in_url = f"{web_app_url}/auth?token={token.token}"

        # In production, always use button. In development, check if URL is public
        use_button = settings.is_production or not any(x in web_app_url.lower() for x in ['localhost', '127.0.0.1', '0.0.0.0'])

        if use_button:
            # Create inline keyboard with sign-in button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Open Web Interface", url=sign_in_url)]
            ])

            await message.answer(
                "📦 <b>File Too Large for Direct Upload</b>\n\n"
                f"File size: {file_size / 1024 / 1024:.2f} MB\n"
                f"Maximum for bot: 20 MB\n\n"
                "✨ Use our web interface to upload larger files (up to 100 MB)!\n\n"
                "Click the button below to access the web interface with a secure one-time login link. "
                "Your profile and balance will be synchronized automatically.\n\n"
                "⏰ <i>Link expires in 24 hours</i>",
                reply_markup=keyboard
            )
        else:
            # Send link as text for localhost development
            await message.answer(
                "📦 <b>File Too Large for Direct Upload</b>\n\n"
                f"File size: {file_size / 1024 / 1024:.2f} MB\n"
                f"Maximum for bot: 20 MB\n\n"
                "✨ Use our web interface to upload larger files (up to 100 MB)!\n\n"
                "🔗 <b>Your one-time login link:</b>\n"
                f"<code>{sign_in_url}</code>\n\n"
                "⏰ <i>Link expires in 24 hours</i>\n\n"
                "⚠️ <b>Note:</b> For production use, please configure a public URL (use ngrok for testing or deploy to a server)."
            )
        return

    # Send processing message
    processing_msg = await message.answer(
        "⏳ <b>Processing your file...</b>\n\n"
        "This may take a few moments depending on the file size."
    )

    try:
        # Initialize wallet service
        wallet_service = WalletService()

        # Calculate cost
        total_cost = await wallet_service.calculate_transcription_cost(duration, media_type)

        # Check balance
        if not await wallet_service.check_sufficient_balance(user, total_cost):
            await processing_msg.edit_text(
                f"❌ <b>Insufficient balance</b>\n\n"
                f"Cost: {total_cost:.2f} UZS\n"
                f"Your balance: {wallet.balance:.2f} UZS\n\n"
                f"Please use /topup to add funds to your account."
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

        # Check Telegram file size limit based on Bot API server type
        max_download_size = settings.max_downloadable_file_size
        max_download_size_mb = max_download_size / 1024 / 1024

        if file_size > max_download_size:
            api_type = "custom Bot API server" if settings.bot_api_server else "standard Telegram Bot API"
            await processing_msg.edit_text(
                f"❌ <b>File Too Large</b>\n\n"
                f"File size: {file_size / 1024 / 1024:.2f} MB\n"
                f"Maximum allowed: {max_download_size_mb:.0f} MB ({api_type})\n\n"
                f"{'Please send a smaller file or compress it before uploading.' if not settings.bot_api_server else 'To process larger files up to ' + str(settings.ai.max_file_size_mb) + ' MB, configure a custom Bot API server.'}"
            )
            return

        # Download file
        bot = message.bot
        file = await bot.get_file(file_id)
        file_io = await bot.download_file(file.file_path)
        file_bytes = file_io.read() if hasattr(file_io, 'read') else file_io

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

        # Generate unique reference ID
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_ref = f"transcription_{file_id}_{timestamp}_{str(uuid.uuid4())[:8]}"

        # Deduct from wallet
        deduct_result = await wallet_service.deduct_balance(
            user=user,
            amount=total_cost,
            description=f"Transcription of {media_type} ({duration // 60}:{duration % 60:02d})",
            reference_id=unique_ref
        )

        if not deduct_result.success:
            await processing_msg.edit_text(
                "❌ <b>Payment Error</b>\n\n"
                f"Error: {deduct_result.error}\n\n"
                "Please try again later."
            )
            return

        # Save transcription to database using Django ORM
        @sync_to_async
        def save_transcription():
            return Transcription.objects.create(
                user_id=user.id,
                file_telegram_id=file_id,
                file_type=media_type,
                file_size=file_size,
                duration_seconds=duration,
                transcription_text=transcription_text,
                cost=total_cost,
                status="completed"
            )

        transcription = await save_transcription()

        # Update wallet balance in memory
        wallet.balance = deduct_result.balance_after

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
            # reply_markup=get_transcription_keyboard(str(transcription.id))
        )

        # Delete processing message
        await processing_msg.delete()

        # Ask for rating (simplified)
        await asyncio.sleep(2)
        await message.answer(
            "⭐ <b>Rate this transcription</b>\n\n"
            "How satisfied are you with the quality?",
            # reply_markup=get_rating_keyboard()  # Disabled for demo
        )

        logger.info(
            f"Transcription completed: {media_type}, {duration}s, cost: {total_cost}"
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
async def handle_rating(callback: CallbackQuery):
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
async def download_transcription(callback: CallbackQuery):
    """Handle transcription download request (disabled in demo mode)"""
    await callback.answer("Download feature is disabled in demo mode!", show_alert=True)


# Handle media sent without command
@router.message(AudioFilter())
@router.message(VideoFilter())
async def handle_direct_media(message: Message, state: FSMContext, user, wallet):
    """Handle media sent directly without using menu"""
    # Extract media info
    if message.audio:
        await process_media_file(message, state, user, wallet, "audio", message.audio.duration, message.audio.file_id, message.audio.file_size)
    elif message.voice:
        await process_media_file(message, state, user, wallet, "audio", message.voice.duration, message.voice.file_id, message.voice.file_size)
    elif message.video:
        await process_media_file(message, state, user, wallet, "video", message.video.duration, message.video.file_id, message.video.file_size)
    else:
        await message.answer("❌ Unsupported media type.")