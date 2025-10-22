import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored console log formatter"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        console: bool = True,
        file: bool = True,
        json_format: bool = False,
        colored: bool = True,
) -> None:
    """
    Setup logging configuration

    Args:
        level: Logging level
        log_dir: Directory for log files
        console: Enable console logging
        file: Enable file logging
        json_format: Use JSON format for logs
        colored: Use colored output for console
    """

    # Create log directory if needed
    if file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        if json_format:
            console_formatter = JsonFormatter()
        elif colored and sys.stdout.isatty():
            console_formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if file and log_dir:
        # Main log file
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=10  # 10 MB
        )
        file_handler.setLevel(logging.DEBUG)

        if json_format:
            file_formatter = JsonFormatter()
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log", maxBytes=10 * 1024 * 1024, backupCount=10  # 10 MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

    # Configure third-party loggers
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={level}, console={console}, file={file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter for adding context to logs
    """

    def __init__(self, logger: logging.Logger, extra: dict):
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        # Add extra context to all log messages
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.extra)
        return msg, kwargs


def get_context_logger(
        name: str, user_id: Optional[int] = None, request_id: Optional[str] = None, **kwargs
) -> LoggerAdapter:
    """
    Get logger with context

    Args:
        name: Logger name
        user_id: User ID for context
        request_id: Request ID for context
        **kwargs: Additional context

    Returns:
        Logger adapter with context
    """
    logger = get_logger(name)
    extra = {}

    if user_id:
        extra["user_id"] = user_id
    if request_id:
        extra["request_id"] = request_id

    extra.update(kwargs)

    return LoggerAdapter(logger, extra)


# Convenience functions for module-level logging
def log_debug(message: str, **kwargs):
    """Log debug message"""
    get_logger("core").debug(message, extra=kwargs)


def log_info(message: str, **kwargs):
    """Log info message"""
    get_logger("core").info(message, extra=kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message"""
    get_logger("core").warning(message, extra=kwargs)


def log_error(message: str, exc_info: bool = False, **kwargs):
    """Log error message"""
    get_logger("core").error(message, exc_info=exc_info, extra=kwargs)


def log_critical(message: str, exc_info: bool = False, **kwargs):
    """Log critical message"""
    get_logger("core").critical(message, exc_info=exc_info, extra=kwargs)


# Default logger instance for easy importing
logger = get_logger("core")
