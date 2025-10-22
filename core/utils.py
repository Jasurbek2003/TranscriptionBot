import hashlib
import hmac
import json
import random
import re
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any


class SecurityUtils:
    """Security utility functions"""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate random token"""
        characters = string.ascii_letters + string.digits
        return "".join(random.choices(characters, k=length))

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate OTP code"""
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()

    @staticmethod
    def verify_password(password: str, salt: str, hashed: str) -> bool:
        """Verify password against hash"""
        return SecurityUtils.hash_password(password, salt) == hashed

    @staticmethod
    def generate_signature(data: str, secret: str) -> str:
        """Generate HMAC signature"""
        return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(data: str, secret: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected = SecurityUtils.generate_signature(data, secret)
        return hmac.compare_digest(expected, signature)


class DateTimeUtils:
    """DateTime utility functions"""

    @staticmethod
    def now() -> datetime:
        """Get current UTC datetime"""
        return datetime.utcnow()

    @staticmethod
    def timestamp() -> int:
        """Get current timestamp"""
        return int(datetime.utcnow().timestamp())

    @staticmethod
    def add_days(date: datetime, days: int) -> datetime:
        """Add days to datetime"""
        return date + timedelta(days=days)

    @staticmethod
    def add_hours(date: datetime, hours: int) -> datetime:
        """Add hours to datetime"""
        return date + timedelta(hours=hours)

    @staticmethod
    def format_datetime(date: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string"""
        return date.strftime(format)

    @staticmethod
    def parse_datetime(date_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """Parse string to datetime"""
        return datetime.strptime(date_str, format)

    @staticmethod
    def get_age(birth_date: datetime) -> int:
        """Calculate age from birth date"""
        today = datetime.today()
        return (
                today.year
                - birth_date.year
                - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

    @staticmethod
    def is_expired(expiry_date: datetime) -> bool:
        """Check if date has expired"""
        return datetime.utcnow() > expiry_date


class StringUtils:
    """String utility functions"""

    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to slug"""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text.strip("-")

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """Truncate text to specified length"""
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number"""
        if len(phone) < 7:
            return phone
        return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address"""
        parts = email.split("@")
        if len(parts) != 2:
            return email
        username = parts[0]
        if len(username) <= 2:
            masked = username[0] + "*"
        else:
            masked = username[0] + "*" * (len(username) - 2) + username[-1]
        return f"{masked}@{parts[1]}"

    @staticmethod
    def capitalize_words(text: str) -> str:
        """Capitalize first letter of each word"""
        return " ".join(word.capitalize() for word in text.split())


class ValidationUtils:
    """Validation utility functions"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number (Uzbek format)"""
        pattern = r"^\+998[0-9]{9}"
        return bool(re.match(pattern, phone))

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Validate username"""
        pattern = r"^[a-zA-Z0-9_]{3,32}"
        return bool(re.match(pattern, username))

    @staticmethod
    def is_strong_password(password: str) -> bool:
        """Check if password is strong"""
        if len(password) < 8:
            return False
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)
        return has_upper and has_lower and has_digit and has_special


class MoneyUtils:
    """Money/currency utility functions"""

    @staticmethod
    def format_amount(amount: Decimal, currency: str = "UZS") -> str:
        """Format amount with currency"""
        return f"{amount:,.2f} {currency}"

    @staticmethod
    def calculate_fee(amount: Decimal, fee_rate: Decimal) -> Decimal:
        """Calculate fee amount"""
        return (amount * fee_rate).quantize(Decimal("0.01"))

    @staticmethod
    def add_fee(amount: Decimal, fee_rate: Decimal) -> Decimal:
        """Add fee to amount"""
        fee = MoneyUtils.calculate_fee(amount, fee_rate)
        return amount + fee

    @staticmethod
    def subtract_fee(amount: Decimal, fee_rate: Decimal) -> Decimal:
        """Subtract fee from amount"""
        fee = MoneyUtils.calculate_fee(amount, fee_rate)
        return amount - fee


class JsonUtils:
    """JSON utility functions"""

    @staticmethod
    def safe_parse(json_str: str, default: Any = None) -> Any:
        """Safely parse JSON string"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def pretty_json(data: Any, indent: int = 2) -> str:
        """Convert to pretty JSON string"""
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)

    @staticmethod
    def compact_json(data: Any) -> str:
        """Convert to compact JSON string"""
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False, default=str)


class FileUtils:
    """File utility functions"""

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        parts = filename.rsplit(".", 1)
        return parts[1].lower() if len(parts) > 1 else ""

    @staticmethod
    def generate_filename(prefix: str, extension: str) -> str:
        """Generate unique filename"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_str = SecurityUtils.generate_token(8)
        return f"{prefix}_{timestamp}_{random_str}.{extension}"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size to human readable"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
