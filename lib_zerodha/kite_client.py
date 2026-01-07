"""Core KiteClient orchestrating all modules."""

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime, date

from .auth.kite_auth import KiteAuth
from .auth.session_manager import SessionManager
from .orders.kite_orders import KiteOrders
from .market_data.kite_market_data import KiteMarketData
from .portfolio.kite_portfolio import KitePortfolio
from .derivatives.kite_fo import KiteFO
from .config import config
from .storage.base_storage import BaseStorage
from .storage.memory_storage import create_memory_storage
from .exceptions.api_exceptions import (
    LibZerodhaError, AuthenticationError, ConfigurationError
)
from .models.market_data import Quote, HistoricalData, Tick
from .models.portfolio import Position, Holding, Portfolio
from .models.derivatives import FOInstrument, OptionChain


class KiteClient:
    """Main client for Kite Connect API integration.
    
    This is the primary interface that orchestrates all modules:
    - Authentication and session management
    - Order placement and management
    - Market data retrieval
    - Portfolio tracking
    - Derivatives trading
    - Data storage and caching
    """
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None,
                 access_token: Optional[str] = None, request_token: Optional[str] = None,
                 storage: Optional[Dict[str, BaseStorage]] = None,
                 config_obj: Optional[object] = None):
        """Initialize KiteClient.
        
        Args:
            api_key: Kite Connect API key
            api_secret: API secret for authentication
            access_token: Existing access token (optional)
            request_token: Request token for session generation (optional)
            storage: Storage implementations (defaults to memory)
            config: Configuration manager (optional)
        """
        # Store credentials
        self.api_key = api_key
        self.api_secret = api_secret
        self.request_token = request_token  # Store request_token
        
        # Configuration
        self.config = config_obj or config
        
        # Storage
        self.storage = storage or create_memory_storage()
        
        # Core modules
        self.auth = KiteAuth(
            api_key=api_key,
            api_secret=api_secret
        )
        
        self.session_manager = SessionManager(
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Set access token if provided
        if access_token:
            self.auth.access_token = access_token
        
        # Trading modules (initialized after authentication)
        self._orders = None
        self._market_data = None
        self._portfolio = None
        self._derivatives = None
        
        # Instruments cache
        self._instruments_df = None
    
    def __str__(self) -> str:
        """String representation of KiteClient."""
        return f"KiteClient(api_key={self.api_key})"
    
    def __repr__(self) -> str:
        """Repr representation of KiteClient."""
        return f"KiteClient(api_key={self.api_key}, access_token={'***' if self.auth.access_token else None})"
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated."""
        if not self.auth.is_authenticated():
            raise AuthenticationError("Access token required for authenticated requests")
    
    def _init_trading_modules(self) -> None:
        """Initialize trading modules after authentication."""
        if not self.auth.is_authenticated():
            return
        
        if self._orders is None:
            self._orders = KiteOrders(
                api_key=self.auth.api_key,
                access_token=self.auth.access_token,
                config=self.config
            )
        
        if self._market_data is None:
            self._market_data = KiteMarketData(
                api_key=self.auth.api_key,
                access_token=self.auth.access_token,
                storage=self.storage,
                config=self.config
            )
        
        if self._portfolio is None:
            self._portfolio = KitePortfolio(
                api_key=self.auth.api_key,
                access_token=self.auth.access_token,
                storage=self.storage.get('portfolio'),
                config=self.config
            )
        
        if self._derivatives is None:
            self._derivatives = KiteFO(
                api_key=self.auth.api_key,
                access_token=self.auth.access_token,
                market_data=self._market_data,
                config=self.config
            )
    
    # Authentication methods
    def get_login_url(self) -> str:
        """Get login URL for Kite Connect authentication."""
        return self.auth.get_login_url()
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Generate session using request token."""
        session_data = self.auth.generate_session(request_token)
        
        # Save session
        self.session_manager.save_session(
            user_id=session_data.get('user_id', 'default'),
            session_data=session_data
        )
        
        # Initialize trading modules
        self._init_trading_modules()
        
        return session_data
    
    def login(self, request_token: str) -> Dict[str, Any]:
        """Login using request token (alias for generate_session)."""
        return self.generate_session(request_token)
    
    def set_access_token(self, access_token: str) -> None:
        """Set access token directly."""
        self.auth.set_access_token(access_token)
        self._init_trading_modules()
    
    def logout(self) -> None:
        """Logout and clear session."""
        self.auth.logout()
        self.session_manager.clear_session()
        
        # Clear trading modules
        self._orders = None
        self._market_data = None
        self._portfolio = None
        self._derivatives = None
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.auth.is_authenticated()
    
    # Market data methods
    def get_quote(self, instruments: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes for instruments."""
        self._ensure_authenticated()
        return self._market_data.get_quote(instruments)
    
    def get_historical_data(self, instrument_token: int, 
                           from_date: date, to_date: date,
                           interval: str = "day", 
                           continuous: bool = False,
                           oi: bool = False) -> List[HistoricalData]:
        """Get historical data for instrument."""
        self._ensure_authenticated()
        return self._market_data.get_historical_data(
            instrument_token, from_date, to_date, interval, continuous, oi
        )
    
    def get_instruments(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """Get instruments list."""
        self._ensure_authenticated()
        return self._market_data.get_instruments(exchange)
    
    # Order methods
    def place_order(self, **order_params) -> str:
        """Place a new order."""
        self._ensure_authenticated()
        return self._orders.place_order(**order_params)
    
    def modify_order(self, order_id: str, **order_params) -> None:
        """Modify an existing order."""
        self._ensure_authenticated()
        return self._orders.modify_order(order_id, **order_params)
    
    def cancel_order(self, order_id: str) -> None:
        """Cancel an order."""
        self._ensure_authenticated()
        return self._orders.cancel_order(order_id)
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders for the day."""
        self._ensure_authenticated()
        return self._orders.get_orders()
    
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get order history for specific order."""
        self._ensure_authenticated()
        return self._orders.get_order_history(order_id)
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all trades for the day."""
        self._ensure_authenticated()
        return self._orders.get_trades()
    
    # Portfolio methods
    def get_positions(self) -> Dict[str, List[Position]]:
        """Get portfolio positions."""
        self._ensure_authenticated()
        return self._portfolio.get_positions()
    
    def get_holdings(self) -> List[Holding]:
        """Get portfolio holdings."""
        self._ensure_authenticated()
        return self._portfolio.get_holdings()
    
    def get_margins(self) -> Dict[str, Dict[str, float]]:
        """Get account margins."""
        self._ensure_authenticated()
        return self._portfolio.get_margins()
    
    def convert_position(self, **conversion_params) -> None:
        """Convert position product type."""
        self._ensure_authenticated()
        return self._portfolio.convert_position(**conversion_params)
    
    # Derivatives methods
    def get_option_chain(self, symbol: str, expiry: date, 
                        strike_range: Optional[tuple] = None) -> OptionChain:
        """Get option chain for symbol and expiry."""
        self._ensure_authenticated()
        return self._derivatives.get_option_chain(symbol, expiry, strike_range)
    
    def get_fo_instruments(self, symbol: Optional[str] = None, 
                          expiry: Optional[date] = None) -> List[FOInstrument]:
        """Get F&O instruments."""
        self._ensure_authenticated()
        return self._derivatives.get_fo_instruments(symbol, expiry)
    
    def place_fo_order(self, **order_params) -> str:
        """Place F&O order with validation."""
        self._ensure_authenticated()
        return self._derivatives.place_fo_order(**order_params)
    
    def get_next_expiry_dates(self, symbol: str, count: int = 6) -> List[date]:
        """Get next expiry dates for symbol."""
        return self._derivatives.get_next_expiry_dates(symbol, count)
    
    # Utility methods
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        self._ensure_authenticated()
        return self.auth.get_profile()
    
    def get_session_data(self) -> Optional[Dict[str, Any]]:
        """Get current session data."""
        profile = self.auth.get_profile() if self.is_authenticated() else None
        user_id = profile.get('user_id', 'default') if profile else 'default'
        return self.session_manager.get_session(user_id)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all modules."""
        status = {
            'authenticated': self.is_authenticated(),
            'modules': {
                'auth': True,
                'session_manager': True,
                'orders': self._orders is not None,
                'market_data': self._market_data is not None,
                'portfolio': self._portfolio is not None,
                'derivatives': self._derivatives is not None,
            },
            'storage': {
                name: storage is not None 
                for name, storage in self.storage.items()
            },
            'config': {
                'environment': self.config.environment,
                'base_url': self.config.base_url
            }
        }
        
        # Test API connectivity if authenticated
        if self.is_authenticated():
            try:
                profile = self.get_profile()
                status['api_connectivity'] = True
                status['user_id'] = profile.get('user_id')
            except Exception as e:
                status['api_connectivity'] = False
                status['api_error'] = str(e)
        
        return status
    
    def close(self) -> None:
        """Close all resources and connections."""
        # Close storage connections
        for storage in self.storage.values():
            if hasattr(storage, 'close'):
                storage.close()
        
        # Clear session
        self.session_manager.clear_session()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # Properties for easy access to modules
    @property
    def orders(self) -> KiteOrders:
        """Get orders module."""
        self._ensure_authenticated()
        return self._orders
    
    @property
    def market_data(self) -> KiteMarketData:
        """Get market data module."""
        self._ensure_authenticated()
        return self._market_data
    
    @property
    def portfolio(self) -> KitePortfolio:
        """Get portfolio module."""
        self._ensure_authenticated()
        return self._portfolio
    
    @property
    def derivatives(self) -> KiteFO:
        """Get derivatives module."""
        self._ensure_authenticated()
        return self._derivatives