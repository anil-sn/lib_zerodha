"""Testing environment configuration."""

from .base_config import Config


class TestingConfig(Config):
    """Testing-specific configuration."""
    
    DEBUG = True
    TESTING = True
    
    # Mock URLs for testing
    BASE_URL = "http://localhost:8000/mock/kite"
    LOGIN_URL = "http://localhost:8000/mock/login"
    
    # API Settings
    TIMEOUT = 5
    MAX_REQUESTS_PER_SECOND = 100  # No rate limiting in tests
    RETRY_ATTEMPTS = 1  # Fail fast in tests
    
    # Database
    DATABASE_URL = "sqlite:///:memory:"
    DATABASE_POOL_SIZE = 1
    
    # WebSocket
    WEBSOCKET_RECONNECT_DELAY = 0.1
    WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 3
    
    # Logging
    LOG_LEVEL = "DEBUG"
    LOG_FILE = None  # No file logging in tests
    
    # Cache
    CACHE_TTL = 1  # Very short TTL for tests
    CACHE_MAX_SIZE = 100
    
    # Test Settings
    MOCK_RESPONSES = True
    GENERATE_TEST_DATA = True