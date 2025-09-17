from .database import (
    Base,
    # DatabaseManager,
    # db_manager,
    init_database,
    close_database,
    get_session,
    # DatabaseUtils
)

from .exceptions import (
    BaseError,
    DatabaseError,
    PaymentError,
    TranscriptionError,
    NotificationError,
    AuthenticationError,
    ValidationError,
    ServiceError,
    BusinessLogicError
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
    VIDEO_PRICE_PER_MINUTE
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
    CacheKeys
)

from .models import (
    BaseModel,
    ExtendedBaseModel,
    TimestampMixin,
    SoftDeleteMixin,
    UUIDMixin,
    MetadataMixin,
    AuditMixin,
    StatusMixin, Base
)

from .utils import (
    SecurityUtils,
    DateTimeUtils,
    StringUtils,
    ValidationUtils,
    MoneyUtils,
    JsonUtils,
    FileUtils
)

from .logging import setup_logging, get_logger

__all__ = [
    # Database
    "Base",
    # "DatabaseManager",
    # "db_manager",
    "init_database",
    "close_database",
    "get_session",
    # "DatabaseUtils",

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

    # Constants
    "NotificationTypes",
    "ErrorCodes",

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

    # Models
    "BaseModel",
    "ExtendedBaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "UUIDMixin",
    "MetadataMixin",
    "AuditMixin",
    "StatusMixin",

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
    "get_logger"
]

__version__ = "1.0.0"