"""Custom exceptions for lib_zerodha."""

class KiteException(Exception):
    """Base exception for all Kite-related errors."""
    pass

class AuthenticationError(KiteException):
    """Raised when authentication fails."""
    pass

class APIError(KiteException):
    """Raised when API returns an error."""
    
    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code

class NetworkError(KiteException):
    """Raised when network operations fail."""
    pass

class ConnectionError(KiteException):
    """Raised when connection operations fail."""
    pass

class DataError(KiteException):
    """Raised when data processing fails."""
    pass

class DatabaseError(KiteException):
    """Raised when database operations fail."""
    pass

class StorageError(KiteException):
    """Raised when storage operations fail."""
    pass

class WebSocketError(KiteException):
    """Raised when WebSocket operations fail."""
    pass

class RateLimitError(KiteException):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after
