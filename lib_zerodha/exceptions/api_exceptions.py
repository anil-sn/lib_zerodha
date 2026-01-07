"""Comprehensive exception classes for lib_zerodha."""

from typing import Optional, Any, Dict


class LibZerodhaError(Exception):
    """Base exception class for lib_zerodha."""
    
    def __init__(self, message: str, error_type: Optional[str] = None, 
                 error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_type = error_type
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            'error_class': self.__class__.__name__,
            'message': self.message,
            'error_type': self.error_type,
            'error_code': self.error_code,
            'context': self.context
        }


# Authentication Exceptions
class AuthenticationError(LibZerodhaError):
    """Authentication related errors."""
    pass


class SessionExpiredError(AuthenticationError):
    """Session has expired."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid API credentials."""
    pass


class TwoFactorAuthError(AuthenticationError):
    """Two-factor authentication required or failed."""
    pass


# Network and API Exceptions
class NetworkError(LibZerodhaError):
    """Network related errors."""
    pass


class APIError(LibZerodhaError):
    """General API errors from Kite Connect."""
    pass


class RateLimitError(APIError):
    """API rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    """Server-side errors (5xx)."""
    pass


class ServiceUnavailableError(ServerError):
    """Service temporarily unavailable."""
    pass


# Validation Exceptions
class ValidationError(LibZerodhaError):
    """Data validation errors."""
    pass


class InvalidParameterError(ValidationError):
    """Invalid parameter value."""
    pass


class MissingParameterError(ValidationError):
    """Required parameter missing."""
    pass


class InvalidFormatError(ValidationError):
    """Invalid data format."""
    pass


# Trading Exceptions
class OrderError(LibZerodhaError):
    """Order related errors."""
    pass


class OrderRejectedError(OrderError):
    """Order rejected by exchange or broker."""
    pass


class InsufficientFundsError(OrderError):
    """Insufficient funds to place order."""
    pass


class MarginError(OrderError):
    """Margin related errors."""
    pass


class PositionError(LibZerodhaError):
    """Position related errors."""
    pass


class InsufficientQuantityError(PositionError):
    """Insufficient quantity for operation."""
    pass


# Market Data Exceptions
class MarketDataError(LibZerodhaError):
    """Market data related errors."""
    pass


class InstrumentNotFoundError(MarketDataError):
    """Instrument not found."""
    pass


class DataNotAvailableError(MarketDataError):
    """Requested data not available."""
    pass


class HistoricalDataError(MarketDataError):
    """Historical data retrieval errors."""
    pass


# WebSocket Exceptions
class WebSocketError(LibZerodhaError):
    """WebSocket related errors."""
    pass


class ConnectionError(WebSocketError):
    """WebSocket connection errors."""
    pass


class SubscriptionError(WebSocketError):
    """Instrument subscription errors."""
    pass


# Storage Exceptions
class StorageError(LibZerodhaError):
    """Storage related errors."""
    pass


class DatabaseError(StorageError):
    """Database operation errors."""
    pass


class CacheError(StorageError):
    """Cache operation errors."""
    pass


# Configuration Exceptions
class ConfigurationError(LibZerodhaError):
    """Configuration related errors."""
    pass


class InvalidConfigError(ConfigurationError):
    """Invalid configuration values."""
    pass


class MissingConfigError(ConfigurationError):
    """Required configuration missing."""
    pass


# Backward compatibility aliases
KiteException = LibZerodhaError
DataError = MarketDataError


# Error code mapping
ERROR_CODE_MAPPING = {
    # Authentication errors
    'TokenException': InvalidCredentialsError,
    'PermissionException': AuthenticationError,
    'UserException': AuthenticationError,
    
    # Order errors
    'OrderException': OrderError,
    'InputException': ValidationError,
    
    # Network errors
    'NetworkException': NetworkError,
    'DataException': MarketDataError,
    
    # Rate limiting
    'TooManyRequests': RateLimitError,
}


def create_exception_from_response(response_data: Dict[str, Any]) -> LibZerodhaError:
    """Create appropriate exception from API response.
    
    Args:
        response_data: API response data
        
    Returns:
        Appropriate exception instance
    """
    message = response_data.get('message', 'Unknown error')
    error_type = response_data.get('error_type', 'GeneralException')
    status_code = response_data.get('status_code')
    
    # Map error type to exception class
    exception_class = ERROR_CODE_MAPPING.get(error_type, APIError)
    
    # Handle HTTP status codes
    if status_code:
        if status_code == 429:
            exception_class = RateLimitError
        elif status_code >= 500:
            exception_class = ServerError
        elif status_code == 401:
            exception_class = AuthenticationError
        elif status_code == 403:
            exception_class = AuthenticationError
        elif status_code == 400:
            exception_class = ValidationError
    
    return exception_class(
        message=message,
        error_type=error_type,
        error_code=str(status_code) if status_code else None,
        context=response_data
    )
