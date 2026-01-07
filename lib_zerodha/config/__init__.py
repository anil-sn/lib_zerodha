"""Configuration management module."""

import os
from typing import Type

from .base_config import Config
from .development import DevelopmentConfig
from .production import ProductionConfig
from .testing import TestingConfig
from .sandbox import SandboxConfig


def get_config() -> Type[Config]:
    """Get configuration based on environment variable.
    
    Returns:
        Configuration class based on LIB_ZERODHA_ENV environment variable.
        Defaults to DevelopmentConfig if not set.
    """
    env = os.getenv('LIB_ZERODHA_ENV', 'development').lower()
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'sandbox': SandboxConfig,
    }
    
    return config_map.get(env, DevelopmentConfig)


# Default configuration instance
config = get_config().from_env()

__all__ = [
    'Config', 'DevelopmentConfig', 'ProductionConfig', 
    'TestingConfig', 'SandboxConfig', 'get_config', 'config'
]