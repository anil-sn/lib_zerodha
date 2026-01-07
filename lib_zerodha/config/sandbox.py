"""Sandbox environment configuration for Kite Connect."""

from .base_config import Config


class SandboxConfig(Config):
    """Sandbox-specific configuration for testing with Kite Connect sandbox."""
    
    DEBUG = True
    TESTING = False
    
    # Kite Connect Sandbox URLs
    BASE_URL = "https://api.kite.trade"  # Same as production for now
    LOGIN_URL = "https://kite.trade/connect/login"
    
    # API Settings
    TIMEOUT = 10
    MAX_REQUESTS_PER_SECOND = 10
    RETRY_ATTEMPTS = 3
    
    # Database
    DATABASE_URL = "sqlite:///lib_zerodha_sandbox.db"
    DATABASE_POOL_SIZE = 5
    
    # WebSocket
    WEBSOCKET_RECONNECT_DELAY = 3
    WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 10
    
    # Logging
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "lib_zerodha_sandbox.log"
    
    # Cache
    CACHE_TTL = 300  # 5 minutes
    CACHE_MAX_SIZE = 1000
    
    # Sandbox Settings
    USE_SANDBOX_DATA = True
    SANDBOX_API_KEY = "sandbox_api_key"
    MOCK_REAL_MONEY_OPERATIONS = True