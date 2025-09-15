from enum import Enum, IntEnum


class UserRole(str, Enum):
    """User roles"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    DELETED = "deleted"


class TransactionType(str, Enum):
    """Transaction types"""
    CREDIT = "credit"  # Money in
    DEBIT = "debit"  # Money out
    REFUND = "refund"
    BONUS = "bonus"
    COMMISSION = "commission"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment methods"""
    PAYME = "payme"
    CLICK = "click"
    PAYZE = "payze"
    WALLET = "wallet"
    BONUS = "bonus"
    ADMIN = "admin"


class TranscriptionStatus(str, Enum):
    """Transcription status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaType(str, Enum):
    """Media file types"""
    AUDIO = "audio"
    VIDEO = "video"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"


class Language(str, Enum):
    """Supported languages"""
    EN = "en"  # English
    RU = "ru"  # Russian
    UZ = "uz"  # Uzbek

    @classmethod
    def get_name(cls, code: str) -> str:
        names = {
            cls.EN: "English",
            cls.RU: "Русский",
            cls.UZ: "O'zbek"
        }
        return names.get(code, "Unknown")

    @classmethod
    def get_flag(cls, code: str) -> str:
        flags = {
            cls.EN: "🇬🇧",
            cls.RU: "🇷🇺",
            cls.UZ: "🇺🇿"
        }
        return flags.get(code, "🏳️")


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Priority(IntEnum):
    """Priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class CacheKeys(str, Enum):
    """Redis cache key prefixes"""
    USER = "user"
    WALLET = "wallet"
    TRANSACTION = "transaction"
    TRANSCRIPTION = "transcription"
    RATE_LIMIT = "rate_limit"
    SESSION = "session"
    STATS = "stats"
    SETTINGS = "settings"

    def key(self, *args) -> str:
        """Generate cache key"""
        parts = [self.value] + [str(arg) for arg in args]
        return ":".join(parts)


class FileStatus(str, Enum):
    """File processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    DELETED = "deleted"
    ERROR = "error"


class AdminAction(str, Enum):
    """Admin action types for logging"""
    USER_EDIT = "user_edit"
    USER_BLOCK = "user_block"
    USER_UNBLOCK = "user_unblock"
    BALANCE_ADJUST = "balance_adjust"
    BROADCAST_SEND = "broadcast_send"
    SETTINGS_CHANGE = "settings_change"
    PRICE_UPDATE = "price_update"
    MAINTENANCE_TOGGLE = "maintenance_toggle"


class WebhookEvent(str, Enum):
    """Webhook event types"""
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    TRANSCRIPTION_COMPLETE = "transcription.complete"
    USER_REGISTERED = "user.registered"
    USER_BLOCKED = "user.blocked"


class QualityLevel(str, Enum):
    """Transcription quality levels"""
    FAST = "fast"  # Lower accuracy, faster processing
    NORMAL = "normal"  # Balanced
    HIGH = "high"  # Higher accuracy, slower processing

    @classmethod
    def get_multiplier(cls, level: str) -> float:
        """Get price multiplier for quality level"""
        multipliers = {
            cls.FAST: 0.8,
            cls.NORMAL: 1.0,
            cls.HIGH: 1.5
        }
        return multipliers.get(level, 1.0)


class ResponseCode(IntEnum):
    """API response codes"""
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# Regex Patterns
class Patterns:
    """Common regex patterns"""
    PHONE_UZ = r"^\+998[0-9]{9}$"
    PHONE_SIMPLE = r"^[0-9]{9}$"
    CARD_NUMBER = r"^[0-9]{13,19}$"
    USERNAME = r"^[a-zA-Z0-9_]{3,32}$"
    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    UUID = r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"