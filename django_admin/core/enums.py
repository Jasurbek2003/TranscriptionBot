"""Core enumerations for the application."""

from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    CREDIT = "credit"
    DEBIT = "debit"
    BONUS = "bonus"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    PAYME = "payme"
    CLICK = "click"
    CASH = "cash"
    CARD = "card"
    OTHER = "other"


class TranscriptionStatus(str, Enum):
    """Transcription status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaType(str, Enum):
    """Media type enumeration."""

    AUDIO = "audio"
    VIDEO = "video"
    VIDEO_NOTE = "video_note"


class QualityLevel(str, Enum):
    """Transcription quality level enumeration."""

    NORMAL = "normal"
    HIGH = "high"
    PREMIUM = "premium"
