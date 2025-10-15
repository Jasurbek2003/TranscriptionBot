from typing import Final

# API Constants
API_VERSION: Final[str] = "v1"
API_PREFIX: Final[str] = f"/api/{API_VERSION}"
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# File Constants
ALLOWED_AUDIO_EXTENSIONS: Final[set] = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma'}
ALLOWED_VIDEO_EXTENSIONS: Final[set] = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
ALLOWED_DOCUMENT_EXTENSIONS: Final[set] = {'.txt', '.pdf', '.doc', '.docx'}

AUDIO_MIME_TYPES: Final[set] = {
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/ogg',
    'audio/mp4', 'audio/aac', 'audio/flac', 'audio/x-ms-wma'
}
VIDEO_MIME_TYPES: Final[set] = {
    'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-matroska',
    'video/webm', 'video/x-flv', 'video/x-ms-wmv'
}

# Size Limits (in bytes)
MAX_AUDIO_SIZE: Final[int] = 100 * 1024 * 1024  # 100 MB
MAX_VIDEO_SIZE: Final[int] = 300 * 1024 * 1024  # 300 MB
MAX_DOCUMENT_SIZE: Final[int] = 20 * 1024 * 1024  # 20 MB

# Duration Limits (in seconds)
MAX_AUDIO_DURATION: Final[int] = 3600  # 1 hour
MAX_VIDEO_DURATION: Final[int] = 1800  # 30 minutes
MIN_MEDIA_DURATION: Final[int] = 1  # 1 second

# Payment Constants
MIN_PAYMENT_AMOUNT: Final[float] = 1000.0  # UZS
MAX_PAYMENT_AMOUNT: Final[float] = 1000000.0  # UZS
INITIAL_BALANCE: Final[float] = 1000.0  # UZS
COMMISSION_RATE: Final[float] = 0.02  # 2%

# Pricing (per minute)
AUDIO_PRICE_PER_MINUTE: Final[float] = 100.0  # UZS
VIDEO_PRICE_PER_MINUTE: Final[float] = 150.0  # UZS

# Rate Limiting
DEFAULT_RATE_LIMIT: Final[int] = 10  # requests
RATE_LIMIT_WINDOW: Final[int] = 60  # seconds
MEDIA_RATE_LIMIT: Final[int] = 3  # media files
MEDIA_RATE_WINDOW: Final[int] = 60  # seconds

# Cache TTL (in seconds)
CACHE_TTL_SHORT: Final[int] = 300  # 5 minutes
CACHE_TTL_MEDIUM: Final[int] = 3600  # 1 hour
CACHE_TTL_LONG: Final[int] = 86400  # 24 hours


# Notification Types
class NotificationTypes:
    TRANSCRIPTION_READY = "transcription_ready"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    BALANCE_LOW = "balance_low"
    SYSTEM_MAINTENANCE = "system_maintenance"
    PROMOTION = "promotion"
    GENERAL = "general"


# Error Codes
class ErrorCodes:
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    VALIDATION_ERROR = 1001
    NOT_FOUND = 1404
    UNAUTHORIZED = 1401
    FORBIDDEN = 1403

    # Database errors (2000-2999)
    DATABASE_ERROR = 2000
    DUPLICATE_RECORD = 2001
    RECORD_NOT_FOUND = 2002

    # Payment errors (3000-3999)
    PAYMENT_ERROR = 3000
    INSUFFICIENT_BALANCE = 3001
    INVALID_AMOUNT = 3002
    PAYMENT_PROVIDER_ERROR = 3003
    TRANSACTION_FAILED = 3004

    # Transcription errors (4000-4999)
    TRANSCRIPTION_ERROR = 4000
    MEDIA_PROCESSING_ERROR = 4001
    FILE_SIZE_ERROR = 4002
    DURATION_ERROR = 4003
    UNSUPPORTED_FORMAT = 4004

    # Service errors (5000-5999)
    SERVICE_ERROR = 5000
    EXTERNAL_API_ERROR = 5001
    RATE_LIMIT_ERROR = 5002
    MAINTENANCE_MODE = 5003
