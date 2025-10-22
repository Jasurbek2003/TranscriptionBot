# bot/handlers/start.py

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards.inline_keyboards import get_settings_keyboard
from bot.utils.messages import get_help_message

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # Clear any states
    await state.clear()

    # Check if user is admin
    is_admin = message.from_user.id in settings.admin_ids

    # Send simple welcome message
    welcome_text = (
        f"👋 Welcome to TranscriptionBot, {message.from_user.first_name}!\n\n"
        f"🎵 Send me audio or video files and I'll transcribe them for you.\n\n"
        f"Use /help to see available commands."
    )

    await message.answer(text=welcome_text)

    logger.info(f"User {message.from_user.id} started the bot")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = get_help_message()
    await message.answer(help_text)


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Handle /balance command"""
    # For now, show a placeholder balance since database is disabled
    balance = 1000.0  # Default balance
    await message.answer(
        f"💰 <b>Your Balance</b>\n\n"
        f"Current balance: {balance:.2f} UZS\n\n"
        f"💡 <i>Note: Database features temporarily disabled for development.</i>\n"
        f"Use /topup to add funds (coming soon)."
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command - show bot information"""
    await message.answer(
        "🤖 <b>Bot Status</b>\n\n"
        "✅ Bot is online\n"
        "✅ Database: SQLite (connected)\n"
        "✅ Transcription: Gemini AI ready\n"
        "⚠️ Payment system: Development mode\n\n"
        "Send /help for available commands."
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Show main menu"""
    is_admin = message.from_user.id in settings.admin_ids
    await message.answer("📱 Main Menu - Coming soon! Use /help for available commands.")


@router.message(F.text == "ℹ️ Help")
async def help_button(message: Message):
    """Handle help button"""
    await cmd_help(message)


@router.message(F.text == "⚙️ Settings")
async def settings_button(message: Message):
    """Handle settings button"""
    await message.answer(
        "⚙️ <b>Settings</b>\n\nChoose what you want to configure:",
        reply_markup=get_settings_keyboard(),
    )


# @router.callback_query(F.data == "settings:language")
# async def settings_language(callback: CallbackQuery, user):
#     """Handle language settings - temporarily disabled"""
#     pass

# @router.callback_query(F.data.startswith("lang:"))
# async def change_language(callback: CallbackQuery, session: AsyncSession, user):
#     """Handle language change - temporarily disabled"""
#     pass


@router.callback_query(F.data == "settings:notifications")
async def settings_notifications(callback: CallbackQuery):
    """Handle notification settings"""
    # Future enhancement: Allow users to configure:
    # - Completion notifications (when transcription is done)
    # - Payment notifications (successful/failed payments)
    # - Balance low warnings
    # - Promotional messages
    await callback.answer(
        "Notification settings will be available in a future update!\n\n"
        "Currently, you receive notifications for:\n"
        "• Completed transcriptions\n"
        "• Payment confirmations",
        show_alert=True,
    )


@router.callback_query(F.data == "settings:transcription")
async def settings_transcription(callback: CallbackQuery):
    """Handle transcription settings"""
    # Future enhancement: Allow users to configure:
    # - Default quality level (fast/normal/high)
    # - Preferred language for transcription
    # - Auto-translate options
    # - Output format preferences
    await callback.answer(
        "Transcription settings will be available in a future update!\n\n"
        "Currently, all transcriptions use:\n"
        "• Normal quality (balanced speed & accuracy)\n"
        "• Auto-detected language\n"
        "• Plain text format",
        show_alert=True,
    )


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    """Go back to main menu"""
    await callback.message.answer("📱 Main Menu - Use /help for available commands.")
    await callback.message.delete()
    await callback.answer()


# Basic transcription functionality
@router.message(F.audio)
async def handle_audio(message: Message):
    """Handle audio files - basic transcription"""
    try:
        # Send processing message
        processing_msg = await message.answer("🎵 Processing your audio file...")

        # Get file info
        audio = message.audio
        file_size_mb = (audio.file_size or 0) / 1024 / 1024
        duration_min = (audio.duration or 0) / 60

        # Basic validation
        if file_size_mb > settings.ai.max_file_size_mb:
            await processing_msg.edit_text(
                f"❌ File too large!\n"
                f"Maximum size: {settings.ai.max_file_size_mb} MB\n"
                f"Your file: {file_size_mb:.1f} MB"
            )
            return

        if duration_min > (settings.ai.max_audio_duration_seconds / 60):
            await processing_msg.edit_text(
                f"❌ Audio too long!\n"
                f"Maximum duration: {settings.ai.max_audio_duration_seconds // 60} minutes\n"
                f"Your audio: {duration_min:.1f} minutes"
            )
            return

        # Placeholder transcription (replace with actual AI service later)
        await processing_msg.edit_text(
            "✅ <b>Audio Transcription Complete!</b>\n\n"
            f"📁 <b>File:</b> {audio.file_name or 'audio.mp3'}\n"
            f"⏱ <b>Duration:</b> {duration_min:.1f} minutes\n"
            f"📊 <b>Size:</b> {file_size_mb:.1f} MB\n\n"
            f"📝 <b>Transcription:</b>\n"
            f"<i>This is a placeholder transcription. "
            f"The actual AI transcription service will be implemented soon.</i>\n\n"
            f"💰 <b>Cost:</b> {duration_min * settings.pricing.audio_price_per_min:.0f} UZS"
        )

    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await message.answer("❌ Error processing audio file. Please try again.")


@router.message(F.voice)
async def handle_voice(message: Message):
    """Handle voice messages"""
    try:
        processing_msg = await message.answer("🎤 Processing your voice message...")

        voice = message.voice
        duration_min = (voice.duration or 0) / 60
        file_size_mb = (voice.file_size or 0) / 1024 / 1024

        # Basic validation
        if duration_min > (settings.ai.max_audio_duration_seconds / 60):
            await processing_msg.edit_text(
                f"❌ Voice message too long!\n"
                f"Maximum: {settings.ai.max_audio_duration_seconds // 60} minutes\n"
                f"Your message: {duration_min:.1f} minutes"
            )
            return

        # Placeholder transcription
        await processing_msg.edit_text(
            "✅ <b>Voice Message Transcribed!</b>\n\n"
            f"⏱ <b>Duration:</b> {duration_min:.1f} minutes\n"
            f"📊 <b>Size:</b> {file_size_mb:.1f} MB\n\n"
            f"📝 <b>Transcription:</b>\n"
            f"<i>This is a placeholder transcription for your voice message. "
            f"Actual transcription coming soon!</i>\n\n"
            f"💰 <b>Cost:</b> {duration_min * settings.pricing.audio_price_per_min:.0f} UZS"
        )

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await message.answer("❌ Error processing voice message. Please try again.")


@router.message(F.video)
async def handle_video(message: Message):
    """Handle video files"""
    try:
        processing_msg = await message.answer("🎬 Processing your video file...")

        video = message.video
        duration_min = (video.duration or 0) / 60
        file_size_mb = (video.file_size or 0) / 1024 / 1024

        # Basic validation
        if file_size_mb > settings.ai.max_file_size_mb:
            await processing_msg.edit_text(
                f"❌ Video file too large!\n"
                f"Maximum size: {settings.ai.max_file_size_mb} MB\n"
                f"Your file: {file_size_mb:.1f} MB"
            )
            return

        if duration_min > (settings.ai.max_video_duration_seconds / 60):
            await processing_msg.edit_text(
                f"❌ Video too long!\n"
                f"Maximum: {settings.ai.max_video_duration_seconds // 60} minutes\n"
                f"Your video: {duration_min:.1f} minutes"
            )
            return

        # Placeholder transcription
        await processing_msg.edit_text(
            "✅ <b>Video Transcription Complete!</b>\n\n"
            f"📁 <b>File:</b> {video.file_name or 'video.mp4'}\n"
            f"⏱ <b>Duration:</b> {duration_min:.1f} minutes\n"
            f"📊 <b>Size:</b> {file_size_mb:.1f} MB\n"
            f"🎞 <b>Resolution:</b> {video.width}x{video.height}\n\n"
            f"📝 <b>Transcription:</b>\n"
            f"<i>This is a placeholder transcription for your video. "
            f"The bot will extract audio and transcribe it once AI service is fully implemented.</i>\n\n"
            f"💰 <b>Cost:</b> {duration_min * settings.pricing.video_price_per_min:.0f} UZS"
        )

    except Exception as e:
        logger.error(f"Video processing error: {e}")
        await message.answer("❌ Error processing video file. Please try again.")


@router.message(F.video_note)
async def handle_video_note(message: Message):
    """Handle video notes (circles)"""
    try:
        processing_msg = await message.answer("⭕ Processing your video note...")

        video_note = message.video_note
        duration_min = (video_note.duration or 0) / 60
        file_size_mb = (video_note.file_size or 0) / 1024 / 1024

        # Basic validation
        if duration_min > (settings.ai.max_video_duration_seconds / 60):
            await processing_msg.edit_text(
                f"❌ Video note too long!\n"
                f"Maximum: {settings.ai.max_video_duration_seconds // 60} minutes\n"
                f"Your note: {duration_min:.1f} minutes"
            )
            return

        # Placeholder transcription
        await processing_msg.edit_text(
            "✅ <b>Video Note Transcribed!</b>\n\n"
            f"⏱ <b>Duration:</b> {duration_min:.1f} minutes\n"
            f"📊 <b>Size:</b> {file_size_mb:.1f} MB\n\n"
            f"📝 <b>Transcription:</b>\n"
            f"<i>This is a placeholder transcription for your video note. "
            f"Actual transcription coming soon!</i>\n\n"
            f"💰 <b>Cost:</b> {duration_min * settings.pricing.video_price_per_min:.0f} UZS"
        )

    except Exception as e:
        logger.error(f"Video note processing error: {e}")
        await message.answer("❌ Error processing video note. Please try again.")


# Add a fallback for unsupported media
@router.message(F.document)
async def handle_document(message: Message):
    """Handle document files"""
    doc = message.document
    if doc.mime_type and ("audio" in doc.mime_type or "video" in doc.mime_type):
        await message.answer(
            "📎 <b>Media Document Detected!</b>\n\n"
            f"📁 <b>File:</b> {doc.file_name}\n"
            f"📊 <b>Size:</b> {(doc.file_size or 0) / 1024 / 1024:.1f} MB\n\n"
            "ℹ️ For best results, please send audio/video files directly instead of as documents.\n\n"
            "🔄 <i>Document transcription support coming soon!</i>"
        )
    else:
        await message.answer(
            "❓ <b>Unsupported File Type</b>\n\n"
            "I can only transcribe:\n"
            "🎵 Audio files (mp3, wav, etc.)\n"
            "🎬 Video files (mp4, avi, etc.)\n"
            "🎤 Voice messages\n"
            "⭕ Video notes\n\n"
            "Please send a supported media file."
        )


@router.message(Command("transcribe"))
async def cmd_transcribe(message: Message):
    """Handle /transcribe command - show instructions"""
    await message.answer(
        "🎵 <b>How to Transcribe Media</b>\n\n"
        "Just send me any of these types of media:\n\n"
        "📤 <b>Supported formats:</b>\n"
        "🎵 Audio files (MP3, WAV, M4A, OGG, FLAC)\n"
        "🎬 Video files (MP4, AVI, MOV, MKV, WebM)\n"
        "🎤 Voice messages\n"
        "⭕ Video notes (circles)\n\n"
        "📊 <b>Limits:</b>\n"
        f"• Max file size: {settings.ai.max_file_size_mb} MB\n"
        f"• Max audio duration: {settings.ai.max_audio_duration_seconds // 60} minutes\n"
        f"• Max video duration: {settings.ai.max_video_duration_seconds // 60} minutes\n\n"
        "💡 <b>Tips:</b>\n"
        "• Clear audio works best\n"
        "• Avoid background noise\n"
        "• Send files directly (not as documents)\n\n"
        "Ready? Send me your media file! 🚀"
    )


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Handle /support command"""
    await message.answer(
        "🆘 <b>Support & Help</b>\n\n"
        "Need help? Here are your options:\n\n"
        "📚 <b>Common questions:</b>\n"
        "• Use /help for bot instructions\n"
        "• Use /status to check bot health\n"
        "• Use /transcribe for transcription guide\n\n"
        "🔧 <b>Technical issues:</b>\n"
        "• File too large? Check /transcribe for limits\n"
        "• Poor quality? Use clear audio/video\n"
        "• Not working? Try /status to check bot\n\n"
        "📞 <b>Contact support:</b>\n"
        "• Telegram: @support (coming soon)\n"
        "• Email: support@example.com\n\n"
        "💡 This is a development version of the bot."
    )


@router.message(F.text.startswith("/"))
async def handle_unknown_command(message: Message):
    """Handle unknown commands"""
    command = message.text.split()[0]
    await message.answer(
        f"❓ <b>Unknown Command:</b> <code>{command}</code>\n\n"
        "📝 <b>Available commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show help information\n"
        "/balance - Check your balance\n"
        "/transcribe - Transcription guide\n"
        "/status - Bot status\n"
        "/support - Get support\n\n"
        "💡 Or just send me audio/video files to transcribe!"
    )
