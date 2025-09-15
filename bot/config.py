from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
BOT_DIR = BASE_DIR / "bot"
LOGS_DIR = BASE_DIR / "logs"
MEDIA_DIR = BASE_DIR / "media"

# Create necessary directories
LOGS_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)
(MEDIA_DIR / "audio").mkdir(exist_ok=True)
(MEDIA_DIR / "video").mkdir(exist_ok=True)
(MEDIA_DIR / "transcriptions").mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Bot configuration settings"""

    # Bot settings
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    BOT_USERNAME: Optional[str] = Field(None, env="BOT_USERNAME")
    DROP_PENDING_UPDATES: bool = Field(False, env="DROP_PENDING_UPDATES")

    # Admin settings
    ADMIN_IDS: List[int] = Field(default_factory=list, env="ADMIN_IDS")
    SUPPORT_CHAT_ID: Optional[str] = Field(None, env="SUPPORT_CHAT_ID")
    DEVELOPER_CHAT_ID: Optional[int] = Field(None, env="DEVELOPER_CHAT_ID")

    # Database settings
    DB_HOST: str = Field("localhost", env="DB_HOST")
    DB_PORT: int = Field(5432, env="DB_PORT")
    DB_NAME: str = Field("transcription_bot", env="DB_NAME")
    DB_USER: str = Field("postgres", env="DB_USER")
    DB_PASSWORD: str = Field("postgres", env="DB_PASSWORD")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis settings
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Payment settings
    PAYME_MERCHANT_ID: str = Field("", env="PAYME_MERCHANT_ID")
    PAYME_SECRET_KEY: str = Field("", env="PAYME_SECRET_KEY")
    PAYME_TEST_MODE: bool = Field(True, env="PAYME_TEST_MODE")

    CLICK_MERCHANT_ID: str = Field("", env="CLICK_MERCHANT_ID")
    CLICK_SERVICE_ID: str = Field("", env="CLICK_SERVICE_ID")
    CLICK_SECRET_KEY: str = Field("", env="CLICK_SECRET_KEY")
    CLICK_TEST_MODE: bool = Field(True, env="CLICK_TEST_MODE")

    # Pricing settings (per minute)
    AUDIO_PRICE_PER_MIN: float = Field(100.0, env="AUDIO_PRICE_PER_MIN")
    VIDEO_PRICE_PER_MIN: float = Field(150.0, env="VIDEO_PRICE_PER_MIN")
    INITIAL_BALANCE: float = Field(1000.0, env="INITIAL_BALANCE")
    MIN_PAYMENT_AMOUNT: float = Field(1000.0, env="MIN_PAYMENT_AMOUNT")
    MAX_PAYMENT_AMOUNT: float = Field(1000000.0, env="MAX_PAYMENT_AMOUNT")

    # AI Service settings
    GEMINI_API_KEY: str = Field("", env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field("gemini-1.5-flash", env="GEMINI_MODEL")
    MAX_AUDIO_DURATION_SECONDS: int = Field(3600, env="MAX_AUDIO_DURATION_SECONDS")  # 1 hour
    MAX_VIDEO_DURATION_SECONDS: int = Field(1800, env="MAX_VIDEO_DURATION_SECONDS")  # 30 minutes
    MAX_FILE_SIZE_MB: int = Field(50, env="MAX_FILE_SIZE_MB")

    # Rate limiting
    THROTTLE_TIME_WINDOW: int = Field(60, env="THROTTLE_TIME_WINDOW")  # seconds
    THROTTLE_MAX_MESSAGES: int = Field(10, env="THROTTLE_MAX_MESSAGES")
    THROTTLE_MAX_MEDIA: int = Field(3, env="THROTTLE_MAX_MEDIA")

    # Webhook settings (for production)
    WEBHOOK_ENABLED: bool = Field(False, env="WEBHOOK_ENABLED")
    WEBHOOK_HOST: str = Field("", env="WEBHOOK_HOST")
    WEBHOOK_PATH: str = Field("/webhook", env="WEBHOOK_PATH")
    WEBHOOK_PORT: int = Field(8443, env="WEBHOOK_PORT")
    WEBHOOK_CERT: str = Field("", env="WEBHOOK_CERT")

    @property
    def WEBHOOK_URL(self) -> str:
        return f"{self.WEBHOOK_HOST}{self.WEBHOOK_PATH}"

    # Feature flags
    MAINTENANCE_MODE: bool = Field(False, env="MAINTENANCE_MODE")
    DEBUG_MODE: bool = Field(False, env="DEBUG_MODE")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    # Localization
    DEFAULT_LANGUAGE: str = Field("en", env="DEFAULT_LANGUAGE")
    SUPPORTED_LANGUAGES: List[str] = Field(
        default_factory=lambda: ["en", "ru", "uz"],
        env="SUPPORTED_LANGUAGES"
    )

    @validator("ADMIN_IDS", pre=True)
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(id.strip()) for id in v.split(",") if id.strip()]
        return v

    @validator("SUPPORTED_LANGUAGES", pre=True)
    def parse_languages(cls, v):
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",") if lang.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Export commonly used values
BOT_TOKEN = settings.BOT_TOKEN
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
ADMIN_IDS = settings.ADMIN_IDS

# File paths
AUDIO_DIR = MEDIA_DIR / "audio"
VIDEO_DIR = MEDIA_DIR / "video"
TRANSCRIPTIONS_DIR = MEDIA_DIR / "transcriptions"