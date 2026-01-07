"""Production environment configuration."""

from .base_config import Config


class ProductionConfig(Config):
    """Production-specific configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Kite Connect URLs
    BASE_URL = "https://api.kite.trade"
    LOGIN_URL = "https://kite.trade/connect/login"
    
    # API Settings
    TIMEOUT = 7
    MAX_REQUESTS_PER_SECOND = 10  # Production rate limit
    RETRY_ATTEMPTS = 5
    
    # Database
    DATABASE_URL = "sqlite:///lib_zerodha_prod.db"
    DATABASE_POOL_SIZE = 20
    DATABASE_POOL_TIMEOUT = 30
    
    # WebSocket
    WEBSOCKET_RECONNECT_DELAY = 2
    WEBSOCKET_MAX_RECONNECT_ATTEMPTS = 20
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "lib_zerodha_prod.log"
    
    # Cache
    CACHE_TTL = 60  # 1 minute
    CACHE_MAX_SIZE = 10000
    
    # Performance
    CONNECTION_POOL_SIZE = 100
    REQUEST_TIMEOUT = 5