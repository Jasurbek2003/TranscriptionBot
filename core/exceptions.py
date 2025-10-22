from typing import Any, Dict, Optional


class BaseError(Exception):
    """Base exception class for the application"""

    def __init__(
            self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {"error": self.code, "message": self.message, "details": self.details}


# Database Exceptions
class DatabaseError(BaseError):
    """Base database exception"""

    pass


class RecordNotFoundError(DatabaseError):
    """Record not found in database"""

    def __init__(self, model: str, id_: Any):
        super().__init__(
            message=f"{model} with id {id_} not found",
            code="RECORD_NOT_FOUND",
            details={"model": model, "id": id_},
        )


class DuplicateRecordError(DatabaseError):
    """Duplicate record error"""

    def __init__(self, model: str, field: str, value: Any):
        super().__init__(
            message=f"{model} with {field}={value} already exists",
            code="DUPLICATE_RECORD",
            details={"model": model, "field": field, "value": value},
        )


class DatabaseConnectionError(DatabaseError):
    """Database connection error"""

    def __init__(self, details: str = ""):
        super().__init__(
            message=f"Failed to connect to database: {details}", code="DATABASE_CONNECTION_ERROR"
        )


# Payment Exceptions
class PaymentError(BaseError):
    """Base payment exception"""

    pass


class InsufficientBalanceError(PaymentError):
    """Insufficient balance error"""

    def __init__(self, required: float, available: float):
        super().__init__(
            message=f"Insufficient balance. Required: {required}, Available: {available}",
            code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class PaymentProviderError(PaymentError):
    """Payment provider error"""

    def __init__(self, provider: str, error: str):
        super().__init__(
            message=f"Payment provider error: {error}",
            code="PAYMENT_PROVIDER_ERROR",
            details={"provider": provider, "error": error},
        )


class TransactionError(PaymentError):
    """Transaction processing error"""

    def __init__(self, transaction_id: str, error: str):
        super().__init__(
            message=f"Transaction {transaction_id} failed: {error}",
            code="TRANSACTION_ERROR",
            details={"transaction_id": transaction_id, "error": error},
        )


class InvalidAmountError(PaymentError):
    """Invalid payment amount"""

    def __init__(self, amount: float, min_amount: float = None, max_amount: float = None):
        details = {"amount": amount}
        if min_amount:
            details["min_amount"] = min_amount
        if max_amount:
            details["max_amount"] = max_amount

        super().__init__(
            message=f"Invalid amount: {amount}", code="INVALID_AMOUNT", details=details
        )


# Transcription Exceptions
class TranscriptionError(BaseError):
    """Base transcription exception"""

    pass


class MediaProcessingError(TranscriptionError):
    """Media file processing error"""

    def __init__(self, file_type: str, error: str):
        super().__init__(
            message=f"Failed to process {file_type}: {error}",
            code="MEDIA_PROCESSING_ERROR",
            details={"file_type": file_type, "error": error},
        )


class TranscriptionServiceError(TranscriptionError):
    """Transcription service error"""

    def __init__(self, service: str, error: str):
        super().__init__(
            message=f"Transcription service error: {error}",
            code="TRANSCRIPTION_SERVICE_ERROR",
            details={"service": service, "error": error},
        )


class FileSizeError(TranscriptionError):
    """File size limit exceeded"""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"File size {size} exceeds maximum {max_size}",
            code="FILE_SIZE_ERROR",
            details={"size": size, "max_size": max_size},
        )


class DurationError(TranscriptionError):
    """Media duration limit exceeded"""

    def __init__(self, duration: int, max_duration: int):
        super().__init__(
            message=f"Duration {duration}s exceeds maximum {max_duration}s",
            code="DURATION_ERROR",
            details={"duration": duration, "max_duration": max_duration},
        )


# Notification Exceptions
class NotificationError(BaseError):
    """Base notification exception"""

    pass


class MessageSendError(NotificationError):
    """Failed to send message"""

    def __init__(self, user_id: int, error: str):
        super().__init__(
            message=f"Failed to send message to user {user_id}: {error}",
            code="MESSAGE_SEND_ERROR",
            details={"user_id": user_id, "error": error},
        )


class UserBlockedBotError(NotificationError):
    """User has blocked the bot"""

    def __init__(self, user_id: int):
        super().__init__(
            message=f"User {user_id} has blocked the bot",
            code="USER_BLOCKED_BOT",
            details={"user_id": user_id},
        )


# Authentication Exceptions
class AuthenticationError(BaseError):
    """Base authentication exception"""

    pass


class UnauthorizedError(AuthenticationError):
    """Unauthorized access"""

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message=message, code="UNAUTHORIZED")


class TokenError(AuthenticationError):
    """Token validation error"""

    def __init__(self, error: str):
        super().__init__(
            message=f"Token error: {error}", code="TOKEN_ERROR", details={"error": error}
        )


# Validation Exceptions
class ValidationError(BaseError):
    """Base validation exception"""

    pass


class InvalidInputError(ValidationError):
    """Invalid input data"""

    def __init__(self, field: str, value: Any, expected: str):
        super().__init__(
            message=f"Invalid {field}: expected {expected}, got {value}",
            code="INVALID_INPUT",
            details={"field": field, "value": value, "expected": expected},
        )


class MissingFieldError(ValidationError):
    """Required field missing"""

    def __init__(self, field: str):
        super().__init__(
            message=f"Required field missing: {field}",
            code="MISSING_FIELD",
            details={"field": field},
        )


# Service Exceptions
class ServiceError(BaseError):
    """Base service exception"""

    pass


class ExternalAPIError(ServiceError):
    """External API error"""

    def __init__(self, service: str, status_code: int, error: str):
        super().__init__(
            message=f"External API error from {service}: {error}",
            code="EXTERNAL_API_ERROR",
            details={"service": service, "status_code": status_code, "error": error},
        )


class RateLimitError(ServiceError):
    """Rate limit exceeded"""

    def __init__(self, limit: int, window: int, retry_after: int = None):
        details = {"limit": limit, "window": window}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            code="RATE_LIMIT_ERROR",
            details=details,
        )


class MaintenanceError(ServiceError):
    """Service is under maintenance"""

    def __init__(self, message: str = "Service is under maintenance"):
        super().__init__(message=message, code="MAINTENANCE_MODE")


# Business Logic Exceptions
class BusinessLogicError(BaseError):
    """Base business logic exception"""

    pass


class OperationNotAllowedError(BusinessLogicError):
    """Operation not allowed"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Operation '{operation}' not allowed: {reason}",
            code="OPERATION_NOT_ALLOWED",
            details={"operation": operation, "reason": reason},
        )


class StateError(BusinessLogicError):
    """Invalid state for operation"""

    def __init__(self, current_state: str, expected_state: str):
        super().__init__(
            message=f"Invalid state: current={current_state}, expected={expected_state}",
            code="INVALID_STATE",
            details={"current_state": current_state, "expected_state": expected_state},
        )
