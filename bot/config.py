"""Bot configuration settings and environment management."""

import os
from pathlib import Path
from typing import List, Optional, Union
from enum import Enum

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
BOT_DIR = BASE_DIR / "bot"
LOGS_DIR = BASE_DIR / "logs"
MEDIA_DIR = BASE_DIR / "media"


class LogLevel(str, Enum):
    """Logging levels enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Language(str, Enum):
    """Supported languages enumeration."""
    ENGLISH = "en"
    RUSSIAN = "ru"
    UZBEK = "uz"


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    directories = [
        LOGS_DIR,
        MEDIA_DIR,
        MEDIA_DIR / "audio",
        MEDIA_DIR / "video",
        MEDIA_DIR / "transcriptions",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    name: str = Field(default="transcription_bot", alias="DB_NAME")
    user: str = Field(default="postgres", alias="DB_USER")
    password: str = Field(default="postgres", alias="DB_PASSWORD")

    @computed_field
    @property
    def url(self) -> str:
        """Generate database connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    db: int = Field(default=0, alias="REDIS_DB")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    @computed_field
    @property
    def url(self) -> str:
        """Generate Redis connection URL."""
        auth_part = f":{self.password}@" if self.password else ""
        return f"redis://{auth_part}{self.host}:{self.port}/{self.db}"


class PaymentSettings(BaseSettings):
    """Payment gateway configuration settings."""

    # PayMe settings
    payme_merchant_id: str = Field(default="", alias="PAYME_MERCHANT_ID")
    payme_secret_key: str = Field(default="", alias="PAYME_SECRET_KEY")
    payme_test_mode: bool = Field(default=True, alias="PAYME_TEST_MODE")

    # Click settings
    click_merchant_id: str = Field(default="", alias="CLICK_MERCHANT_ID")
    click_service_id: str = Field(default="", alias="CLICK_SERVICE_ID")
    click_secret_key: str = Field(default="", alias="CLICK_SECRET_KEY")
    click_test_mode: bool = Field(default=True, alias="CLICK_TEST_MODE")


class PricingSettings(BaseSettings):
    """Pricing configuration settings."""

    audio_price_per_min: float = Field(default=100.0, alias="AUDIO_PRICE_PER_MIN", gt=0)
    video_price_per_min: float = Field(default=150.0, alias="VIDEO_PRICE_PER_MIN", gt=0)
    initial_balance: float = Field(default=1000.0, alias="INITIAL_BALANCE", ge=0)
    min_payment_amount: float = Field(default=1000.0, alias="MIN_PAYMENT_AMOUNT", gt=0)
    max_payment_amount: float = Field(default=1000000.0, alias="MAX_PAYMENT_AMOUNT", gt=0)

    @field_validator("max_payment_amount")
    @classmethod
    def validate_max_payment(cls, v: float, info) -> float:
        """Ensure max payment is greater than min payment."""
        if hasattr(info.data, 'min_payment_amount') and v <= info.data['min_payment_amount']:
            raise ValueError("max_payment_amount must be greater than min_payment_amount")
        return v


class AISettings(BaseSettings):
    """AI service configuration settings."""

    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    max_audio_duration_seconds: int = Field(default=3600, alias="MAX_AUDIO_DURATION_SECONDS", gt=0)
    max_video_duration_seconds: int = Field(default=1800, alias="MAX_VIDEO_DURATION_SECONDS", gt=0)
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB", gt=0)


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""

    time_window: int = Field(default=60, alias="THROTTLE_TIME_WINDOW", gt=0)
    max_messages: int = Field(default=10, alias="THROTTLE_MAX_MESSAGES", gt=0)
    max_media: int = Field(default=3, alias="THROTTLE_MAX_MEDIA", gt=0)


class WebhookSettings(BaseSettings):
    """Webhook configuration settings."""

    enabled: bool = Field(default=False, alias="WEBHOOK_ENABLED")
    host: str = Field(default="", alias="WEBHOOK_HOST")
    path: str = Field(default="/webhook", alias="WEBHOOK_PATH")
    port: int = Field(default=8443, alias="WEBHOOK_PORT", ge=1, le=65535)
    cert: str = Field(default="", alias="WEBHOOK_CERT")

    @computed_field
    @property
    def url(self) -> str:
        """Generate webhook URL."""
        return f"{self.host}{self.path}"


class Settings(BaseSettings):
    """Main application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, alias="ENVIRONMENT")

    # Bot settings
    bot_token: str = Field(alias="BOT_TOKEN")
    bot_username: Optional[str] = Field(default=None, alias="BOT_USERNAME")
    drop_pending_updates: bool = Field(default=False, alias="DROP_PENDING_UPDATES")

    # Admin settings
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    support_chat_id: Optional[str] = Field(default=None, alias="SUPPORT_CHAT_ID")
    developer_chat_id: Optional[int] = Field(default=None, alias="DEVELOPER_CHAT_ID")

    # Feature flags
    maintenance_mode: bool = Field(default=False, alias="MAINTENANCE_MODE")
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")

    # Localization
    default_language: Language = Field(default=Language.ENGLISH, alias="DEFAULT_LANGUAGE")
    supported_languages: List[Language] = Field(
        default_factory=lambda: [Language.ENGLISH, Language.RUSSIAN, Language.UZBEK],
        alias="SUPPORTED_LANGUAGES"
    )

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    payment: PaymentSettings = Field(default_factory=PaymentSettings)
    pricing: PricingSettings = Field(default_factory=PricingSettings)
    ai: AISettings = Field(default_factory=AISettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, List[int]]) -> List[int]:
        print(v, type(v))
        """Parse admin IDs from string or list."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(id.strip()) for id in v.split(",") if id.strip().isdigit()]
        return v or []

    @field_validator("supported_languages", mode="before")
    @classmethod
    def parse_languages(cls, v: Union[str, List[str]]) -> List[Language]:
        """Parse supported languages from string or list."""
        if isinstance(v, str):
            if not v.strip():
                return [Language.ENGLISH, Language.RUSSIAN, Language.UZBEK]
            lang_codes = [lang.strip() for lang in v.split(",") if lang.strip()]
            return [Language(code) for code in lang_codes if code in Language.__members__.values()]
        return v or [Language.ENGLISH, Language.RUSSIAN, Language.UZBEK]

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT


# Initialize directories
ensure_directories()

# Create settings instance
settings = Settings()

# Backward compatibility exports
BOT_TOKEN = settings.bot_token
DATABASE_URL = settings.database.url
REDIS_URL = settings.redis.url
ADMIN_IDS = settings.admin_ids

# Directory paths
AUDIO_DIR = MEDIA_DIR / "audio"
VIDEO_DIR = MEDIA_DIR / "video"
TRANSCRIPTIONS_DIR = MEDIA_DIR / "transcriptions"

# Expose nested settings for convenience
db_settings = settings.database
redis_settings = settings.redis
payment_settings = settings.payment
pricing_settings = settings.pricing
ai_settings = settings.ai
rate_limit_settings = settings.rate_limit
webhook_settings = settings.webhook