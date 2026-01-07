"""Configuration management for lib_zerodha."""

import os
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class Config:
    """Base configuration for Kite Connect API."""
    
    # API Configuration
    api_key: str
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    
    # URLs
    base_url: str = "https://api.kite.trade"
    API_BASE_URL: str = "https://api.kite.trade"  # Alias for compatibility
    LOGIN_URL: str = "https://kite.trade/connect/login"
    websocket_url: str = "wss://ws.kite.trade/"
    
    # Timeouts
    timeout: int = 30
    websocket_timeout: int = 5
    
    # Rate limiting
    max_requests_per_second: int = 10
    
    # Data processing
    enable_caching: bool = True
    cache_ttl_seconds: int = 60
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("KITE_API_KEY", ""),
            api_secret=os.getenv("KITE_API_SECRET"),
            access_token=os.getenv("KITE_ACCESS_TOKEN")
        )
    
    def validate(self) -> bool:
        """Validate required configuration."""
        return bool(self.api_key)

# Global configuration instance
config = Config.from_env()
