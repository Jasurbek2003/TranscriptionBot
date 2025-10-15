"""
Core module - Shared utilities, constants, and exceptions.

This module provides common functionality used across the bot and services.
Database models are now in Django (django_admin/apps/*/models.py).
"""

from .exceptions import (
    BaseError,
    DatabaseError,
    PaymentError,
    TranscriptionError,
    NotificationError,
    AuthenticationError,
    ValidationError,
    ServiceError,
    BusinessLogicError,
    InsufficientBalanceError,
    RecordNotFoundError,
    DuplicateRecordError,
)

from .constants import (
    NotificationTypes,
    ErrorCodes,
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_AUDIO_SIZE,
    MAX_VIDEO_SIZE,
    MIN_PAYMENT_AMOUNT,
    MAX_PAYMENT_AMOUNT,
    AUDIO_PRICE_PER_MINUTE,
    VIDEO_PRICE_PER_MINUTE,
)

from .enums import (
    UserRole,
    UserStatus,
    TransactionType,
    TransactionStatus,
    PaymentMethod,
    TranscriptionStatus,
    MediaType,
    Language,
    Priority,
    CacheKeys,
    QualityLevel,
)

from .utils import (
    SecurityUtils,
    DateTimeUtils,
    StringUtils,
    ValidationUtils,
    MoneyUtils,
    JsonUtils,
    FileUtils,
)

from .logging import setup_logging, get_logger, logger

__all__ = [
    # Exceptions
    "BaseError",
    "DatabaseError",
    "PaymentError",
    "TranscriptionError",
    "NotificationError",
    "AuthenticationError",
    "ValidationError",
    "ServiceError",
    "BusinessLogicError",
    "InsufficientBalanceError",
    "RecordNotFoundError",
    "DuplicateRecordError",

    # Constants
    "NotificationTypes",
    "ErrorCodes",
    "ALLOWED_AUDIO_EXTENSIONS",
    "ALLOWED_VIDEO_EXTENSIONS",
    "MAX_AUDIO_SIZE",
    "MAX_VIDEO_SIZE",
    "MIN_PAYMENT_AMOUNT",
    "MAX_PAYMENT_AMOUNT",
    "AUDIO_PRICE_PER_MINUTE",
    "VIDEO_PRICE_PER_MINUTE",

    # Enums
    "UserRole",
    "UserStatus",
    "TransactionType",
    "TransactionStatus",
    "PaymentMethod",
    "TranscriptionStatus",
    "MediaType",
    "Language",
    "Priority",
    "CacheKeys",
    "QualityLevel",

    # Utils
    "SecurityUtils",
    "DateTimeUtils",
    "StringUtils",
    "ValidationUtils",
    "MoneyUtils",
    "JsonUtils",
    "FileUtils",

    # Logging
    "setup_logging",
    "get_logger",
    "logger",
]

__version__ = "2.0.0"