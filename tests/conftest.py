"""Test configuration and shared fixtures for lib_zerodha.

This module provides a MockKiteServer that replicates the behavior of the 
official Kite Connect API v3 using mock data from the official 
kiteconnect-mocks repository.
"""

import json
import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional
import re
from urllib.parse import urlparse, parse_qs

# Path to mock responses
MOCK_RESPONSES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "mock_responses")

def load_mock_json(filename):
    """Load JSON data from mock responses directory."""
    filepath = os.path.join(MOCK_RESPONSES_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

class MockKiteServer:
    """Simulates the Kite Connect API endpoints and logic."""
    
    def __init__(self):
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"
        self.access_token = "valid_access_token"
        
        # Load official mock data
        self.profile_data = load_mock_json("profile.json")
        self.margins_data = load_mock_json("margins.json")
        self.quote_data = load_mock_json("quote.json")
        self.orders_data = load_mock_json("orders.json")
        self.positions_data = load_mock_json("positions.json")
        self.holdings_data = load_mock_json("holdings.json")
        self.trades_data = load_mock_json("trades.json")
        self.generate_session_data = load_mock_json("generate_session.json")
        
        # State for orders placed during session
        self.session_orders = []
        if self.orders_data and "data" in self.orders_data:
            self.session_orders = self.orders_data["data"]
        
    def handle_request(self, method: str, url: str, query_params: Optional[Dict] = None, **kwargs) -> Mock:
        """Route incoming HTTP requests to the appropriate mock handler."""
        path = url
        params = query_params or {}
        data = kwargs.get('data', {})
        headers = kwargs.get('headers', {})

        # 1. AUTHENTICATION CHECK (Except for login and instruments)
        if path != "/session/token" and not path.startswith("/instruments") and not self._validate_auth(headers):
            return self._response(403, {"status": "error", "message": "Invalid access token", "error_type": "TokenException"})

        # 2. ROUTING
        if path == "/session/token" and method == "POST":
            return self._handle_login(data)
            
        elif path == "/user/profile" and method == "GET":
            return self._response(200, self.profile_data)
            
        elif path == "/user/margins" and method == "GET":
            return self._response(200, self.margins_data)
            
        elif path == "/orders" and method == "GET":
            return self._response(200, {"status": "success", "data": self.session_orders})
            
        elif path.startswith("/orders/") and method == "POST":
            variety = path.split("/")[-1]
            return self._handle_place_order(variety, data)
            
        elif path.startswith("/orders/") and method == "PUT":
            match = re.match(r"/orders/(\w+)/(\w+)", path)
            if match:
                return self._handle_modify_order(match.group(2), data)
                
        elif path.startswith("/orders/") and method == "DELETE":
            match = re.match(r"/orders/(\w+)/(\w+)", path)
            if match:
                return self._handle_cancel_order(match.group(2))
                
        elif path == "/quote" and method == "GET":
            return self._handle_quote(params)
            
        elif path == "/quote/ltp" and method == "GET":
            return self._response(200, load_mock_json("ltp.json"))
            
        elif path == "/quote/ohlc" and method == "GET":
            return self._response(200, load_mock_json("ohlc.json"))
            
        elif path == "/portfolio/positions" and method == "GET":
            return self._response(200, self.positions_data)
            
        elif path == "/portfolio/holdings" and method == "GET":
            return self._response(200, self.holdings_data)
            
        elif path == "/trades" and method == "GET":
            return self._response(200, self.trades_data)
            
        elif path.startswith("/instruments") and method == "GET":
            return self._handle_instruments(path)
            
        return self._response(404, {"status": "error", "message": "Route not found", "error_type": "GeneralException"})

    # --- Handlers ---

    def _validate_auth(self, headers: Dict) -> bool:
        """Verify Authorization header format and token."""
        auth_header = headers.get("Authorization", "")
        # Official format: token api_key:access_token
        expected = f"token {self.api_key}:{self.access_token}"
        return auth_header == expected

    def _handle_login(self, data: Dict) -> Mock:
        """Handle login flow."""
        if data.get("api_key") == self.api_key and "request_token" in data:
            resp_data = self.generate_session_data.copy()
            if "data" in resp_data:
                resp_data["data"]["api_key"] = self.api_key
                resp_data["data"]["access_token"] = self.access_token
            return self._response(200, resp_data)
        return self._response(403, {"status": "error", "message": "Invalid credentials", "error_type": "TokenException"})

    def _handle_place_order(self, variety: str, data: Dict) -> Mock:
        """Handle order placement."""
        order_id = str(len(self.session_orders) + 100000000000000)
        
        # Mimic official response for order placement
        # { "status": "success", "data": { "order_id": "..." } }
        order_resp = load_mock_json("order_response.json")
        if order_resp and "data" in order_resp:
            order_resp["data"]["order_id"] = order_id
        
        # Add to session orders for subsequent GET /orders
        new_order = {
            "order_id": order_id,
            "status": "OPEN",
            "variety": variety,
            "order_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exchange": data.get("exchange"),
            "tradingsymbol": data.get("tradingsymbol"),
            "transaction_type": data.get("transaction_type"),
            "quantity": int(data.get("quantity", 0)),
            "price": float(data.get("price", 0)),
            "product": data.get("product"),
            "order_type": data.get("order_type"),
        }
        self.session_orders.append(new_order)
        
        return self._response(200, order_resp)

    def _handle_modify_order(self, order_id: str, data: Dict) -> Mock:
        for order in self.session_orders:
            if order["order_id"] == order_id:
                order.update(data)
                order_resp = load_mock_json("order_modify.json")
                if order_resp and "data" in order_resp:
                    order_resp["data"]["order_id"] = order_id
                return self._response(200, order_resp)
        return self._response(400, {"status": "error", "message": "Order not found", "error_type": "InputException"})

    def _handle_cancel_order(self, order_id: str) -> Mock:
        for order in self.session_orders:
            if order["order_id"] == order_id:
                order["status"] = "CANCELLED"
                order_resp = load_mock_json("order_cancel.json")
                if order_resp and "data" in order_resp:
                    order_resp["data"]["order_id"] = order_id
                return self._response(200, order_resp)
        return self._response(400, {"status": "error", "message": "Order not found", "error_type": "InputException"})

    def _handle_quote(self, params: Dict) -> Mock:
        instruments = params.get("i", [])
        if not instruments:
            return self._response(400, {"status": "error", "message": "No instruments specified", "error_type": "InputException"})
            
        # If specific quote.json is available, use it.
        # Otherwise filter from main quote_data if it contains multiple
        return self._response(200, self.quote_data)

    def _handle_instruments(self, path: str) -> Mock:
        # /instruments returns all
        # /instruments/{exchange} returns for exchange
        filename = "instruments_all.csv"
        if "NSE" in path:
            filename = "instruments_nse.csv"
            
        filepath = os.path.join(MOCK_RESPONSES_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            return self._response(200, {}, content=content)
        return self._response(404, {"status": "error", "message": "Instrument file not found"})

    def _response(self, status_code: int, json_data: Any, content: Optional[bytes] = None) -> Mock:
        """Construct a requests.Response mock."""
        mock_resp = Mock()
        mock_resp.status_code = status_code
        
        if content:
            mock_resp.content = content
            mock_resp.text = content.decode('utf-8')
        else:
            mock_resp.json.return_value = json_data
            mock_resp.text = json.dumps(json_data)
        
        # Simulate raise_for_status behavior
        if status_code >= 400:
            msg = json_data.get("message", "API Error") if isinstance(json_data, dict) else "API Error"
            mock_resp.raise_for_status.side_effect = Exception(f"{status_code} Error: {msg}")
        else:
            mock_resp.raise_for_status.return_value = None
            
        return mock_resp


# --- pytest Fixtures ---

@pytest.fixture
def kite_server():
    """Fixture to provide the MockKiteServer instance."""
    return MockKiteServer()

@pytest.fixture(autouse=True)
def patch_requests(kite_server):
    """Automatically patch requests.Session to route to KiteServer."""
    with patch("requests.Session.request") as mock_request:
        def side_effect(method, url, **kwargs):
            # Only intercept Kite API calls
            if "api.kite.trade" in url or "kite.trade" in url:
                parsed_url = urlparse(url)
                path = parsed_url.path
                
                # Merge URL query params and 'params' kwarg
                query_params = parse_qs(parsed_url.query)
                if 'params' in kwargs and kwargs['params']:
                    for k, v in kwargs['params'].items():
                        if isinstance(v, list):
                            query_params.setdefault(k, []).extend(v)
                        else:
                            query_params.setdefault(k, []).append(v)
                
                # Update URL with merged params for handle_request to see them if needed
                # or just pass query_params explicitly if we refactor handle_request.
                # For now, we'll manually handle the params in a way handle_request expects.
                # Actually, handle_request uses parse_qs(parsed_url.query).
                # Let's just pass the merged params to handle_request.
                
                return kite_server.handle_request(method, path, query_params=query_params, **kwargs)
            else:
                return Mock(status_code=404)
        
        mock_request.side_effect = side_effect
        yield mock_request

@pytest.fixture
def mock_kite_client(test_config, tmp_path):
    """KiteClient instance using the Mock Server (via auto-patched requests)."""
    from lib_zerodha import KiteClient
    session_file = str(tmp_path / "session.enc")
    client = KiteClient(
        api_key=test_config.api_key,
        api_secret=test_config.api_secret,
        access_token="valid_access_token",
        session_file=session_file,
        config_obj=test_config
    )
    return client

@pytest.fixture
def test_config():
    """Provide test configuration."""
    from lib_zerodha.config.base_config import Config
    return Config(
        api_key="test_api_key",
        api_secret="test_api_secret",
        access_token=None,
        base_url="https://api.kite.trade",
        websocket_url="wss://ws.kite.trade/",
        timeout=7
    )

@pytest.fixture
def mock_login_response():
    """Mock successful login response."""
    return load_mock_json("generate_session.json")

@pytest.fixture  
def mock_profile_response():
    """Mock user profile response."""
    return load_mock_json("profile.json")
