import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """Notification delivery status"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


class TelegramNotifier:
    """
    Service for sending notifications via Telegram.
    Handles various notification types including text, media, and documents.
    """

    def __init__(self, bot: Bot, default_parse_mode: ParseMode = ParseMode.HTML):
        """
        Initialize Telegram Notifier.

        Args:
            bot: Configured aiogram Bot instance
            default_parse_mode: Default parse mode for messages
        """
        self.bot = bot
        self.default_parse_mode = default_parse_mode
        self._retry_delays = {
            NotificationPriority.LOW: [5, 10, 30],
            NotificationPriority.NORMAL: [3, 8, 20],
            NotificationPriority.HIGH: [2, 5, 10],
            NotificationPriority.URGENT: [1, 3, 5],
        }

    async def send_text_message(
            self,
            chat_id: Union[int, str],
            text: str,
            parse_mode: Optional[ParseMode] = None,
            disable_notification: bool = False,
            reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None,
            disable_web_page_preview: bool = True,
            priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Dict[str, Any]:
        """
        Send a text message to a user.

        Args:
            chat_id: Telegram chat/user ID
            text: Message text
            parse_mode: Text parse mode (HTML, Markdown, etc.)
            disable_notification: Send silently
            reply_markup: Keyboard markup
            disable_web_page_preview: Disable link previews
            priority: Message priority for retry logic

        Returns:
            Dict with status and message info
        """
        parse_mode = parse_mode or self.default_parse_mode

        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )

            logger.info(f"Message sent successfully to {chat_id}")
            return {
                "status": NotificationStatus.SENT,
                "message_id": message.message_id,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except TelegramForbiddenError:
            logger.warning(f"Bot was blocked by user {chat_id}")
            return {
                "status": NotificationStatus.FAILED,
                "error": "User blocked bot",
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except TelegramNotFound:
            logger.error(f"Chat {chat_id} not found")
            return {
                "status": NotificationStatus.FAILED,
                "error": "Chat not found",
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except TelegramRetryAfter as e:
            logger.warning(f"Rate limited. Retry after {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            return await self.send_text_message(
                chat_id,
                text,
                parse_mode,
                disable_notification,
                reply_markup,
                disable_web_page_preview,
                priority,
            )

        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {str(e)}")
            return {
                "status": NotificationStatus.FAILED,
                "error": str(e),
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def send_document(
            self,
            chat_id: Union[int, str],
            document: Union[FSInputFile, BufferedInputFile, str],
            caption: Optional[str] = None,
            parse_mode: Optional[ParseMode] = None,
            disable_notification: bool = False,
            reply_markup: Optional[InlineKeyboardMarkup] = None,
            thumbnail: Optional[Union[FSInputFile, BufferedInputFile, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a document to a user.

        Args:
            chat_id: Telegram chat/user ID
            document: File to send (file_id, FSInputFile, or BufferedInputFile)
            caption: Document caption
            parse_mode: Caption parse mode
            disable_notification: Send silently
            reply_markup: Inline keyboard
            thumbnail: Document thumbnail

        Returns:
            Dict with status and message info
        """
        parse_mode = parse_mode or self.default_parse_mode

        try:
            message = await self.bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=caption,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
                thumbnail=thumbnail,
            )

            logger.info(f"Document sent successfully to {chat_id}")
            return {
                "status": NotificationStatus.SENT,
                "message_id": message.message_id,
                "document_id": message.document.file_id,
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send document to {chat_id}: {str(e)}")
            return {
                "status": NotificationStatus.FAILED,
                "error": str(e),
                "chat_id": chat_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def send_transcription_ready(
            self,
            chat_id: Union[int, str],
            transcription_id: str,
            duration_seconds: int,
            cost: float,
            file_type: str = "audio",
    ) -> Dict[str, Any]:
        """
        Send notification that transcription is ready.

        Args:
            chat_id: User's Telegram ID
            transcription_id: Transcription ID in database
            duration_seconds: Media duration in seconds
            cost: Transcription cost
            file_type: Type of file transcribed (audio/video)

        Returns:
            Notification status
        """
        duration_min = duration_seconds // 60
        duration_sec = duration_seconds % 60

        text = (
            "✅ <b>Transcription Complete!</b>\n\n"
            f"📁 Type: {file_type.capitalize()}\n"
            f"⏱ Duration: {duration_min}:{duration_sec:02d}\n"
            f"💰 Cost: {cost:.2f} UZS\n\n"
            "Your transcription file will be sent shortly."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 View History", callback_data=f"history"),
                    InlineKeyboardButton(text="💳 Check Balance", callback_data=f"balance"),
                ]
            ]
        )

        return await self.send_text_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, priority=NotificationPriority.HIGH
        )

    async def send_payment_confirmation(
            self,
            chat_id: Union[int, str],
            amount: float,
            payment_method: str,
            transaction_id: str,
            new_balance: float,
    ) -> Dict[str, Any]:
        """
        Send payment confirmation notification.

        Args:
            chat_id: User's Telegram ID
            amount: Payment amount
            payment_method: Payment method used
            transaction_id: Transaction ID
            new_balance: New wallet balance

        Returns:
            Notification status
        """
        text = (
            "✅ <b>Payment Successful!</b>\n\n"
            f"💵 Amount: {amount:.2f} UZS\n"
            f"💳 Method: {payment_method}\n"
            f"🆔 Transaction: <code>{transaction_id}</code>\n"
            f"💰 New Balance: {new_balance:.2f} UZS\n\n"
            "Thank you for your payment!"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📊 Transaction History", callback_data="transactions")]
            ]
        )

        return await self.send_text_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, priority=NotificationPriority.HIGH
        )

    async def send_insufficient_balance(
            self,
            chat_id: Union[int, str],
            current_balance: float,
            required_amount: float,
            media_duration_seconds: int,
    ) -> Dict[str, Any]:
        """
        Send insufficient balance notification.

        Args:
            chat_id: User's Telegram ID
            current_balance: Current wallet balance
            required_amount: Required amount for transcription
            media_duration_seconds: Duration of media file

        Returns:
            Notification status
        """
        shortage = required_amount - current_balance
        duration_min = media_duration_seconds // 60
        duration_sec = media_duration_seconds % 60

        text = (
            "❌ <b>Insufficient Balance</b>\n\n"
            f"Media Duration: {duration_min}:{duration_sec:02d}\n"
            f"Required: {required_amount:.2f} UZS\n"
            f"Your Balance: {current_balance:.2f} UZS\n"
            f"Shortage: {shortage:.2f} UZS\n\n"
            "Please top up your balance to continue."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="💳 Top Up Balance", callback_data="topup"),
                    InlineKeyboardButton(text="💰 Check Balance", callback_data="balance"),
                ]
            ]
        )

        return await self.send_text_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, priority=NotificationPriority.NORMAL
        )

    async def send_error_notification(
            self,
            chat_id: Union[int, str],
            error_type: str,
            error_message: str,
            support_contact: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send error notification to user.

        Args:
            chat_id: User's Telegram ID
            error_type: Type of error
            error_message: Error description
            support_contact: Support contact information

        Returns:
            Notification status
        """
        text = (
            "⚠️ <b>An Error Occurred</b>\n\n"
            f"Error Type: {error_type}\n"
            f"Details: {error_message}\n\n"
        )

        if support_contact:
            text += f"If this issue persists, please contact support: {support_contact}"
        else:
            text += "Please try again later or contact support if the issue persists."

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Try Again", callback_data="retry"),
                    InlineKeyboardButton(text="📞 Support", callback_data="support"),
                ]
            ]
        )

        return await self.send_text_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, priority=NotificationPriority.HIGH
        )

    async def send_bulk_notification(
            self,
            chat_ids: List[Union[int, str]],
            text: str,
            parse_mode: Optional[ParseMode] = None,
            disable_notification: bool = True,
            priority: NotificationPriority = NotificationPriority.LOW,
    ) -> Dict[str, Any]:
        """
        Send notification to multiple users.

        Args:
            chat_ids: List of chat IDs
            text: Message text
            parse_mode: Text parse mode
            disable_notification: Send silently
            priority: Message priority

        Returns:
            Dict with success/failure counts
        """
        results = {"total": len(chat_ids), "success": 0, "failed": 0, "failures": []}

        for chat_id in chat_ids:
            result = await self.send_text_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                priority=priority,
            )

            if result["status"] == NotificationStatus.SENT:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failures"].append(
                    {"chat_id": chat_id, "error": result.get("error", "Unknown error")}
                )

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)

        logger.info(
            f"Bulk notification complete: {results['success']}/{results['total']} successful"
        )
        return results

    async def send_maintenance_notification(
            self,
            chat_ids: List[Union[int, str]],
            start_time: datetime,
            end_time: datetime,
            reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send maintenance notification to users.

        Args:
            chat_ids: List of user chat IDs
            start_time: Maintenance start time
            end_time: Estimated end time
            reason: Maintenance reason

        Returns:
            Bulk send results
        """
        text = (
            "🔧 <b>Scheduled Maintenance</b>\n\n"
            f"Start: {start_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"End: {end_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        )

        if reason:
            text += f"Reason: {reason}\n"

        text += "\nThe service will be temporarily unavailable during this time. We apologize for any inconvenience."

        return await self.send_bulk_notification(
            chat_ids=chat_ids,
            text=text,
            disable_notification=False,
            priority=NotificationPriority.HIGH,
        )

    async def edit_message(
            self,
            chat_id: Union[int, str],
            message_id: int,
            text: str,
            parse_mode: Optional[ParseMode] = None,
            reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """
        Edit an existing message.

        Args:
            chat_id: Chat ID
            message_id: Message ID to edit
            text: New text
            parse_mode: Parse mode
            reply_markup: New keyboard markup

        Returns:
            True if successful, False otherwise
        """
        parse_mode = parse_mode or self.default_parse_mode

        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.debug("Message content unchanged, skipping edit")
                return True
            logger.error(f"Failed to edit message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to edit message: {str(e)}")
            return False

    async def delete_message(self, chat_id: Union[int, str], message_id: int) -> bool:
        """
        Delete a message.

        Args:
            chat_id: Chat ID
            message_id: Message ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {str(e)}")
            return False

    async def answer_callback_query(
            self,
            callback_query_id: str,
            text: Optional[str] = None,
            show_alert: bool = False,
            url: Optional[str] = None,
            cache_time: int = 0,
    ) -> bool:
        """
        Answer a callback query.

        Args:
            callback_query_id: Callback query ID
            text: Notification text
            show_alert: Show as alert dialog
            url: URL to open
            cache_time: Cache time in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert,
                url=url,
                cache_time=cache_time,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to answer callback query: {str(e)}")
            return False
