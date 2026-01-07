"""lib_zerodha: Production-ready trading library for Kite Connect API.

A comprehensive, modular trading library that provides:
- Authentication and session management
- Order placement and management
- Market data retrieval (real-time and historical)
- Portfolio tracking and analytics
- Derivatives (F&O) trading support
- Real-time WebSocket data streams
- Flexible storage backends
- Comprehensive error handling

Example usage:
    from lib_zerodha import KiteClient
    
    # Initialize client
    client = KiteClient(
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    # Login
    session = client.generate_session("request_token")
    
    # Place order
    order_id = client.place_order(
        tradingsymbol="RELIANCE",
        exchange="NSE",
        transaction_type="BUY",
        order_type="LIMIT",
        quantity=1,
        price=2500.0,
        product="CNC",
        validity="DAY"
    )
    
    # Get real-time quotes
    quotes = client.get_quote(["NSE:RELIANCE"])
    
    # Access F&O functionality
    option_chain = client.get_option_chain("NIFTY", expiry_date)
"""

from .kite_client import KiteClient
from .config import config
from .storage.memory_storage import create_memory_storage
from .storage.sqlite_storage import create_sqlite_storage

# Core models
from .models.market_data import Quote, HistoricalData, Tick
from .models.portfolio import Position, Holding, Portfolio
from .models.derivatives import FOInstrument, OptionChain, OptionData
from .models.base import Order, Trade

# Authentication
from .auth.kite_auth import KiteAuth
from .auth.session_manager import SessionManager

# Trading modules
from .orders.kite_orders import KiteOrders
from .market_data.kite_market_data import KiteMarketData
from .portfolio.kite_portfolio import KitePortfolio
from .derivatives.kite_fo import KiteFO

# Real-time data
from .realtime.kite_websocket import KiteWebSocket
from .realtime.subscriptions import SubscriptionManager
from .realtime.data_handlers import (
    TickAggregator, MarketDepthProcessor, 
    RealTimeQuoteManager, TickBuffer
)

# Exceptions
from .exceptions.api_exceptions import (
    LibZerodhaError, AuthenticationError, APIError,
    ValidationError, OrderError, MarketDataError,
    WebSocketError, StorageError, SessionExpiredError,
    InvalidCredentialsError, NetworkError, RateLimitError
)

# Order types and enums
from .orders.order_types import (
    OrderType, TransactionType, ProductType, 
    Variety, Exchange, Validity, OrderStatus, InstrumentType
)

# Version info
__version__ = "2.0.0"
__author__ = "lib_zerodha Contributors"
__description__ = "Production-ready trading library for Kite Connect API"

# Main exports
__all__ = [
    # Core client
    "KiteClient",
    
    # Configuration

    
    # Storage
    "create_memory_storage",
    "create_sqlite_storage",
    
    # Models
    "Quote", "HistoricalData", "Tick",
    "Position", "Holding", "Portfolio",
    "FOInstrument", "OptionChain", "OptionData",
    "OrderRequest", "OrderResponse", "TradeResponse",
    
    # Authentication
    "KiteAuth", "SessionManager",
    
    # Trading modules
    "KiteOrders", "KiteMarketData", "KitePortfolio", "KiteFO",
    
    # Real-time
    "KiteWebSocket", "SubscriptionManager",
    "TickAggregator", "MarketDepthProcessor", 
    "RealTimeQuoteManager", "TickBuffer",
    
    # Exceptions
    "LibZerodhaError", "AuthenticationError", "APIError",
    "ValidationError", "OrderError", "MarketDataError",
    "WebSocketError", "StorageError", "SessionExpiredError",
    "InvalidCredentialsError", "NetworkError", "RateLimitError",
    
    # Enums
    "OrderType", "TransactionType", "ProductType",
    "ValidityType", "ExchangeType", "OrderStatus",
    
    # Version
    "__version__"
]


# Convenience functions
def create_client(api_key: str, api_secret: str = None, 
                 access_token: str = None, environment: str = "production",
                 storage_type: str = "memory", **kwargs) -> KiteClient:
    """Create a KiteClient with sensible defaults.
    
    Args:
        api_key: Kite Connect API key
        api_secret: API secret (required for login)
        access_token: Existing access token (optional)
        environment: Environment (production, sandbox, testing)
        storage_type: Storage type (memory, sqlite)
        **kwargs: Additional arguments for client
        
    Returns:
        Configured KiteClient instance
    """
    # Use the global config object
    
    if storage_type == "sqlite":
        storage = create_sqlite_storage()
    else:
        storage = create_memory_storage()
    
    return KiteClient(
        api_key=api_key,
        api_secret=api_secret,
        access_token=access_token,
        storage=storage,
        config=config,
        **kwargs
    )