"""Development environment configuration."""

from .base_config import Config


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Kite Connect URLs
    BASE_URL = "https://api.kite.trade"
    LOGIN_URL = "https://kite.trade/connect/login"
    
    # API Settings
    TIMEOUT = 10
    MAX_REQUESTS_PER_SECOND = 5  # Conservative for development
    RETRY_ATTEMPTS = 3
    
    # Database
    DATABASE_URL = "sqlite:///lib_zerodha_dev.db"
    DATABASE_POOL_SIZE = 5
    
    # WebSocket
    WEBSOCKET_RECONNECT_DELAY = 5
    WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 10
    
    # Logging
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "lib_zerodha_dev.log"
    
    # Cache
    CACHE_TTL = 300  # 5 minutes
    CACHE_MAX_SIZE = 1000