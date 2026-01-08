"""Clean facade client for lib_zerodha - implements Facade Pattern."""

from typing import Optional, Dict, Any, List, Union
from datetime import date
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import KiteAuth, SessionManager
from .orders import KiteOrders
from .market_data import KiteMarketData
from .portfolio import KitePortfolio
from .derivatives import KiteFO
from .realtime import KiteWebSocket
from .config import config
from .exceptions import LibZerodhaError, NetworkError, AuthenticationError
from .storage import BaseStorage, create_memory_storage
from .models.market_data import Quote, HistoricalData


class KiteClient:
    """Clean facade client implementing the Facade Pattern.
    
    This client provides a unified interface to all lib_zerodha functionality
    while delegating actual implementation to specialized modules.
    """
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None,
                 access_token: Optional[str] = None,
                 request_token: Optional[str] = None,
                 storage: Optional[BaseStorage] = None,
                 config_obj: Optional[object] = None,
                 session_file: Optional[str] = None):
        """Initialize Kite client with modular architecture.
        
        Args:
            api_key: Kite Connect API key
            api_secret: API secret for authentication
            access_token: Existing access token (optional)
            request_token: Request token for session generation (optional)
            storage: Storage backend for data persistence
            config_obj: Configuration object
            session_file: Custom path for session storage
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.request_token = request_token
        self.config = config_obj or config
        self.storage = storage or create_memory_storage()
        
        # Setup HTTP session with retries and rate limiting
        self._setup_session()
        
        # Initialize Core components
        self.auth = KiteAuth(api_key, api_secret)
        self.session_manager = SessionManager(
            api_key, api_secret, 
            auth_instance=self.auth,
            session_file=session_file
        )
        
        # Trading modules - delegate all functionality to these
        self.orders = KiteOrders(self.session, self._get_auth_headers)
        self.market_data = KiteMarketData(self.session, self._get_auth_headers)
        self.portfolio = KitePortfolio(self.session, self._get_auth_headers)
        self.derivatives = KiteFO(self.session, self._get_auth_headers)
        
        # Real-time data (initialized when needed)
        self._websocket = None
        
        # Set access token if provided
        if access_token:
            self.auth.access_token = access_token
    
    def _setup_session(self):
        """Setup HTTP session with retries and timeouts."""
        self.session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'lib_zerodha/2.0.0',
            'X-Kite-Version': '3'
        })
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self.auth.access_token:
            raise AuthenticationError("Access token required for authenticated requests")
        
        return {
            "Authorization": f"token {self.api_key}:{self.auth.access_token}",
            "X-Kite-Version": "3"
        }
    
    # --- Authentication Delegate Methods ---
    
    def get_login_url(self) -> str:
        """Get login URL."""
        return self.auth.get_login_url()

    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """Generate session from request token."""
        return self.session_manager.create_session(request_token)

    def login(self, request_token: str) -> Dict[str, Any]:
        """Login and generate session (alias for generate_session)."""
        return self.generate_session(request_token)

    def logout(self) -> bool:
        """Logout and invalidate session."""
        return self.session_manager.invalidate_session()

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.auth.is_authenticated()

    def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        return self.auth.get_profile()

    # --- Market Data Delegate Methods ---

    def get_quote(self, instruments: Union[str, List[str]]) -> Dict[str, Quote]:
        """Get real-time quotes."""
        return self.market_data.get_quote(instruments)

    def get_ltp(self, instruments: Union[str, List[str]]) -> Dict[str, float]:
        """Get Last Traded Price."""
        return self.market_data.get_ltp(instruments)

    def get_ohlc(self, instruments: Union[str, List[str]]) -> Dict[str, Any]:
        """Get OHLC."""
        return self.market_data.get_ohlc(instruments)

    def get_historical_data(self, instrument_token: int, from_date: date, to_date: date, interval: str, **kwargs):
        """Get historical data."""
        return self.market_data.get_historical_data(instrument_token, from_date, to_date, interval, **kwargs)

    def get_instruments(self, exchange: Optional[str] = None):
        """Get list of tradable instruments."""
        return self.market_data.get_instruments(exchange)

    # --- Orders Delegate Methods ---

    def place_order(self, variety: str = "regular", **kwargs) -> str:
        """Place a new order."""
        return self.orders.place_order(variety=variety, **kwargs)

    def modify_order(self, order_id: str, variety: str = "regular", **kwargs) -> str:
        """Modify an existing order."""
        return self.orders.modify_order(order_id=order_id, variety=variety, **kwargs)

    def cancel_order(self, order_id: str, variety: str = "regular") -> str:
        """Cancel an order."""
        return self.orders.cancel_order(order_id=order_id, variety=variety)

    def get_orders(self) -> List[Dict[str, Any]]:
        """Get order book."""
        return self.orders.get_orders()

    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get history for a specific order."""
        return self.orders.get_order_history(order_id)

    def get_trades(self) -> List[Dict[str, Any]]:
        """Get list of executed trades."""
        return self.orders.get_trades()

    # --- GTT Delegate Methods ---

    def get_gtts(self) -> List[Dict[str, Any]]:
        """Get list of GTT triggers."""
        return self.orders.get_gtts()

    def get_gtt(self, trigger_id: int) -> Dict[str, Any]:
        """Get GTT trigger details."""
        return self.orders.get_gtt(trigger_id)

    def place_gtt(self, trigger_type: str, tradingsymbol: str, exchange: str,
                  trigger_values: List[float], last_price: float,
                  orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Place GTT order."""
        return self.orders.place_gtt(trigger_type, tradingsymbol, exchange, 
                                   trigger_values, last_price, orders)

    def modify_gtt(self, trigger_id: int, trigger_type: str, tradingsymbol: str, 
                   exchange: str, trigger_values: List[float], last_price: float,
                   orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Modify GTT order."""
        return self.orders.modify_gtt(trigger_id, trigger_type, tradingsymbol, exchange, 
                                    trigger_values, last_price, orders)

    def delete_gtt(self, trigger_id: int) -> Dict[str, Any]:
        """Delete GTT order."""
        return self.orders.delete_gtt(trigger_id)

    # --- Portfolio Delegate Methods ---

    def get_positions(self):
        """Get current positions."""
        return self.portfolio.get_positions()

    def get_holdings(self):
        """Get current holdings."""
        return self.portfolio.get_holdings()

    def get_margins(self, segment: Optional[str] = None):
        """Get account margins."""
        return self.portfolio.get_margins(segment)

    def convert_position(self,
                        tradingsymbol: str,
                        exchange: str,
                        transaction_type: str,
                        position_type: str,
                        quantity: int,
                        old_product: str,
                        new_product: str) -> bool:
        """Convert position product type."""
        return self.portfolio.convert_position(
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            transaction_type=transaction_type,
            position_type=position_type,
            quantity=quantity,
            old_product=old_product,
            new_product=new_product
        )

    # --- Real-time Delegate Methods ---
    
    @property
    def websocket(self) -> KiteWebSocket:
        """Get lazy-initialized WebSocket client."""
        if self._websocket is None:
            profile = self.auth.get_profile()
            self._websocket = KiteWebSocket(
                api_key=self.api_key,
                access_token=self.auth.access_token,
                user_id=profile.get('user_id'),
                public_token=profile.get('public_token')
            )
        return self._websocket

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._websocket:
            self._websocket.disconnect()

    def __str__(self) -> str:
        return f"KiteClient(api_key={self.api_key})"

    def __repr__(self) -> str:
        return f"<lib_zerodha.kite_client.KiteClient at {hex(id(self))}>"