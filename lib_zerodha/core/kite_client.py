"""Comprehensive Kite Connect REST API client."""

import requests
import hashlib
import urllib.parse
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
import pandas as pd
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import config
from ..exceptions.api_exceptions import APIError, AuthenticationError, LibZerodhaError
from ..models.base import (
    Quote, Instrument, Position, Order, Trade, Holding, 
    MarginInfo, Portfolio, HistoricalData, OHLC
)

class KiteClient:
    """Complete Kite Connect REST API client."""
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None, 
                 access_token: Optional[str] = None, base_url: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.base_url = base_url or config.base_url
        
        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0 / config.max_requests_per_second
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _request(self, method: str, endpoint: str, params: Dict = None, 
                 data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3"
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                timeout=config.timeout
            )
            
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "error":
                raise APIError(
                    result.get("message", "Unknown API error"),
                    result.get("error_type"),
                    response.status_code
                )
            
            return result.get("data", result)
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error: {str(e)}")
    
    # Authentication methods
    def generate_session(self, request_token: str, api_secret: str) -> Dict[str, str]:
        """Generate access token from request token."""
        checksum = hashlib.sha256(
            f"{self.api_key}{request_token}{api_secret}".encode()
        ).hexdigest()
        
        data = {
            "api_key": self.api_key,
            "request_token": request_token,
            "checksum": checksum
        }
        
        result = self._request("POST", "/session/token", data=data)
        self.access_token = result["access_token"]
        return result
    
    def invalidate_session(self) -> bool:
        """Logout and invalidate session."""
        try:
            self._request("DELETE", "/session/token")
            self.access_token = None
            return True
        except APIError:
            return False
    
    def profile(self) -> Dict[str, Any]:
        """Get user profile."""
        return self._request("GET", "/user/profile")
    
    def margins(self, segment: str = None) -> MarginInfo:
        """Get account margins."""
        endpoint = "/user/margins"
        if segment:
            endpoint += f"/{segment}"
        
        data = self._request("GET", endpoint)
        return MarginInfo(
            equity=data.get("equity", {}),
            commodity=data.get("commodity", {})
        )
    
    # Market data methods
    def instruments(self, exchange: str = None) -> List[Instrument]:
        """Get instruments list."""
        endpoint = "/instruments"
        if exchange:
            endpoint += f"/{exchange}"
        
        # This endpoint returns CSV, handle differently
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=config.timeout)
        response.raise_for_status()
        
        # Parse CSV data
        import io
        df = pd.read_csv(io.StringIO(response.text))
        
        instruments = []
        for _, row in df.iterrows():
            instruments.append(Instrument(
                instrument_token=int(row['instrument_token']),
                exchange_token=int(row['exchange_token']),
                tradingsymbol=row['tradingsymbol'],
                name=row['name'],
                last_price=float(row.get('last_price', 0)),
                expiry=pd.to_datetime(row['expiry']) if pd.notna(row['expiry']) else None,
                strike=float(row.get('strike', 0)),
                tick_size=float(row.get('tick_size', 0.05)),
                lot_size=int(row.get('lot_size', 1)),
                instrument_type=row['instrument_type'],
                segment=row['segment'],
                exchange=row['exchange']
            ))
        
        return instruments
    
    def quote(self, instruments: Union[str, List[str]]) -> Dict[str, Quote]:
        """Get real-time quotes."""
        if isinstance(instruments, str):
            instruments = [instruments]
        
        params = {"i": instruments}
        data = self._request("GET", "/quote", params=params)
        
        quotes = {}
        for instrument_key, quote_data in data.items():
            quotes[instrument_key] = Quote(
                instrument_token=quote_data["instrument_token"],
                timestamp=datetime.fromisoformat(quote_data["timestamp"]),
                last_price=quote_data["last_price"],
                ohlc=OHLC(
                    open=quote_data["ohlc"]["open"],
                    high=quote_data["ohlc"]["high"],
                    low=quote_data["ohlc"]["low"],
                    close=quote_data["ohlc"]["close"],
                    volume=quote_data.get("volume", 0)
                ),
                volume=quote_data.get("volume", 0),
                average_price=quote_data.get("average_price", 0),
                oi=quote_data.get("oi", 0),
                oi_day_high=quote_data.get("oi_day_high", 0),
                oi_day_low=quote_data.get("oi_day_low", 0)
            )
        
        return quotes
    
    def ohlc(self, instruments: Union[str, List[str]]) -> Dict[str, OHLC]:
        """Get OHLC data."""
        if isinstance(instruments, str):
            instruments = [instruments]
        
        params = {"i": instruments}
        data = self._request("GET", "/quote/ohlc", params=params)
        
        ohlc_data = {}
        for instrument_key, ohlc_raw in data.items():
            ohlc_data[instrument_key] = OHLC(
                open=ohlc_raw["ohlc"]["open"],
                high=ohlc_raw["ohlc"]["high"],
                low=ohlc_raw["ohlc"]["low"],
                close=ohlc_raw["ohlc"]["close"],
                volume=ohlc_raw.get("volume", 0)
            )
        
        return ohlc_data
    
    def ltp(self, instruments: Union[str, List[str]]) -> Dict[str, float]:
        """Get Last Traded Price."""
        if isinstance(instruments, str):
            instruments = [instruments]
        
        params = {"i": instruments}
        data = self._request("GET", "/quote/ltp", params=params)
        
        return {k: v["last_price"] for k, v in data.items()}
    
    def historical_data(self, instrument_token: int, from_date: date, 
                       to_date: date, interval: str, 
                       continuous: bool = False, oi: bool = False) -> HistoricalData:
        """Get historical data."""
        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"), 
            "interval": interval,
            "continuous": 1 if continuous else 0,
            "oi": 1 if oi else 0
        }
        
        endpoint = f"/instruments/historical/{instrument_token}/{interval}"
        data = self._request("GET", endpoint, params=params)
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data["candles"], 
                         columns=["date", "open", "high", "low", "close", "volume", "oi"])
        
        return HistoricalData(
            instrument_token=instrument_token,
            interval=interval,
            data=df
        )
    
    # Portfolio methods
    def positions(self) -> List[Position]:
        """Get portfolio positions."""
        data = self._request("GET", "/portfolio/positions")
        
        positions = []
        for pos_type in ["net", "day"]:
            for pos_data in data.get(pos_type, []):
                positions.append(Position(
                    tradingsymbol=pos_data["tradingsymbol"],
                    exchange=pos_data["exchange"],
                    instrument_token=pos_data["instrument_token"],
                    product=pos_data["product"],
                    quantity=pos_data["quantity"],
                    overnight_quantity=pos_data["overnight_quantity"],
                    multiplier=pos_data["multiplier"],
                    average_price=pos_data["average_price"],
                    close_price=pos_data["close_price"],
                    last_price=pos_data["last_price"],
                    value=pos_data["value"],
                    pnl=pos_data["pnl"],
                    m2m=pos_data["m2m"],
                    unrealised=pos_data["unrealised"],
                    realised=pos_data["realised"]
                ))
        
        return positions
    
    def holdings(self) -> List[Holding]:
        """Get portfolio holdings."""
        data = self._request("GET", "/portfolio/holdings")
        
        holdings = []
        for holding_data in data:
            holdings.append(Holding(
                tradingsymbol=holding_data["tradingsymbol"],
                exchange=holding_data["exchange"],
                instrument_token=holding_data["instrument_token"],
                isin=holding_data["isin"],
                product=holding_data["product"],
                quantity=holding_data["quantity"],
                t1_quantity=holding_data["t1_quantity"],
                realised_quantity=holding_data["realised_quantity"],
                authorised_quantity=holding_data["authorised_quantity"],
                authorised_date=pd.to_datetime(holding_data["authorised_date"]) if holding_data.get("authorised_date") else None,
                opening_quantity=holding_data["opening_quantity"],
                collateral_quantity=holding_data["collateral_quantity"],
                collateral_type=holding_data["collateral_type"],
                discrepancy=holding_data["discrepancy"],
                average_price=holding_data["average_price"],
                last_price=holding_data["last_price"],
                close_price=holding_data["close_price"],
                pnl=holding_data["pnl"],
                day_change=holding_data["day_change"],
                day_change_percentage=holding_data["day_change_percentage"]
            ))
        
        return holdings
    
    def get_portfolio(self) -> Portfolio:
        """Get complete portfolio data."""
        return Portfolio(
            positions=self.positions(),
            holdings=self.holdings(),
            margin=self.margins()
        )
    
    # Order management methods  
    def place_order(self, exchange: str, tradingsymbol: str, 
                   transaction_type: str, quantity: int, 
                   product: str, order_type: str,
                   price: float = None, trigger_price: float = None,
                   disclosed_quantity: int = None, validity: str = "DAY",
                   tag: str = None) -> str:
        """Place an order."""
        data = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "product": product,
            "order_type": order_type,
            "validity": validity
        }
        
        if price:
            data["price"] = price
        if trigger_price:
            data["trigger_price"] = trigger_price
        if disclosed_quantity:
            data["disclosed_quantity"] = disclosed_quantity
        if tag:
            data["tag"] = tag
        
        result = self._request("POST", "/orders/regular", data=data)
        return result["order_id"]
    
    def modify_order(self, order_id: str, quantity: int = None, 
                    price: float = None, order_type: str = None,
                    trigger_price: float = None, validity: str = None,
                    disclosed_quantity: int = None) -> str:
        """Modify an existing order."""
        data = {}
        if quantity:
            data["quantity"] = quantity
        if price:
            data["price"] = price
        if order_type:
            data["order_type"] = order_type
        if trigger_price:
            data["trigger_price"] = trigger_price
        if validity:
            data["validity"] = validity
        if disclosed_quantity:
            data["disclosed_quantity"] = disclosed_quantity
        
        result = self._request("PUT", f"/orders/regular/{order_id}", data=data)
        return result["order_id"]
    
    def cancel_order(self, order_id: str, variety: str = "regular") -> str:
        """Cancel an order."""
        result = self._request("DELETE", f"/orders/{variety}/{order_id}")
        return result["order_id"]
    
    def orders(self) -> List[Order]:
        """Get all orders for the day."""
        data = self._request("GET", "/orders")
        
        orders = []
        for order_data in data:
            orders.append(Order(
                order_id=order_data["order_id"],
                parent_order_id=order_data.get("parent_order_id"),
                exchange=order_data["exchange"],
                tradingsymbol=order_data["tradingsymbol"],
                instrument_token=order_data["instrument_token"],
                transaction_type=order_data["transaction_type"],
                order_type=order_data["order_type"],
                product=order_data["product"],
                quantity=order_data["quantity"],
                disclosed_quantity=order_data["disclosed_quantity"],
                price=order_data["price"],
                trigger_price=order_data["trigger_price"],
                average_price=order_data["average_price"],
                filled_quantity=order_data["filled_quantity"],
                pending_quantity=order_data["pending_quantity"],
                cancelled_quantity=order_data["cancelled_quantity"],
                status=order_data["status"],
                status_message=order_data["status_message"],
                order_timestamp=pd.to_datetime(order_data["order_timestamp"]),
                exchange_timestamp=pd.to_datetime(order_data["exchange_timestamp"]) if order_data.get("exchange_timestamp") else None,
                variety=order_data["variety"],
                validity=order_data["validity"],
                tag=order_data.get("tag")
            ))
        
        return orders
    
    def order_history(self, order_id: str) -> List[Order]:
        """Get order history/modifications."""
        data = self._request("GET", f"/orders/{order_id}")
        # Convert similar to orders() method
        return [Order(**order_data) for order_data in data]
    
    def trades(self) -> List[Trade]:
        """Get all trades for the day."""
        data = self._request("GET", "/trades")
        
        trades = []
        for trade_data in data:
            trades.append(Trade(
                trade_id=trade_data["trade_id"],
                order_id=trade_data["order_id"],
                exchange=trade_data["exchange"],
                tradingsymbol=trade_data["tradingsymbol"],
                instrument_token=trade_data["instrument_token"],
                transaction_type=trade_data["transaction_type"],
                product=trade_data["product"],
                quantity=trade_data["quantity"],
                average_price=trade_data["average_price"],
                fill_timestamp=pd.to_datetime(trade_data["fill_timestamp"]),
                exchange_timestamp=pd.to_datetime(trade_data["exchange_timestamp"])
            ))
        
        return trades
    
    def order_trades(self, order_id: str) -> List[Trade]:
        """Get trades for a specific order."""
        data = self._request("GET", f"/orders/{order_id}/trades")
        return [Trade(**trade_data) for trade_data in data]
    
    # Position Management Methods
    def convert_position(self, exchange: str, tradingsymbol: str, 
                        transaction_type: str, position_type: str,
                        quantity: int, old_product: str, new_product: str) -> str:
        """Convert position from one product type to another."""
        data = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "position_type": position_type,
            "quantity": quantity,
            "old_product": old_product,
            "new_product": new_product
        }
        
        result = self._request("PUT", "/portfolio/positions", data=data)
        return result.get("status", "success")
    
    def get_auction_instruments(self) -> List[Dict[str, Any]]:
        """Get list of available instruments for auction session."""
        return self._request("GET", "/portfolio/holdings/auctions")
    
    # Mutual Fund Methods
    def mf_orders(self, order_id: str = None) -> Union[List[Dict], Dict]:
        """Get mutual fund orders."""
        if order_id:
            return self._request("GET", f"/mf/orders/{order_id}")
        else:
            return self._request("GET", "/mf/orders")
    
    def place_mf_order(self, tradingsymbol: str, transaction_type: str,
                      quantity: int = None, amount: float = None, 
                      tag: str = None) -> str:
        """Place mutual fund order."""
        data = {
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type
        }
        
        if quantity:
            data["quantity"] = quantity
        if amount:
            data["amount"] = amount
        if tag:
            data["tag"] = tag
        
        result = self._request("POST", "/mf/orders", data=data)
        return result["order_id"]
    
    def cancel_mf_order(self, order_id: str) -> str:
        """Cancel mutual fund order."""
        result = self._request("DELETE", f"/mf/orders/{order_id}")
        return result["order_id"]
    
    def mf_sips(self, sip_id: str = None) -> Union[List[Dict], Dict]:
        """Get mutual fund SIPs."""
        if sip_id:
            return self._request("GET", f"/mf/sips/{sip_id}")
        else:
            return self._request("GET", "/mf/sips")
    
    def place_mf_sip(self, tradingsymbol: str, amount: float, instalments: int,
                    frequency: str, initial_amount: float = None, 
                    instalment_day: int = None, tag: str = None) -> str:
        """Place mutual fund SIP."""
        data = {
            "tradingsymbol": tradingsymbol,
            "amount": amount,
            "instalments": instalments,
            "frequency": frequency
        }
        
        if initial_amount:
            data["initial_amount"] = initial_amount
        if instalment_day:
            data["instalment_day"] = instalment_day
        if tag:
            data["tag"] = tag
        
        result = self._request("POST", "/mf/sips", data=data)
        return result["sip_id"]
    
    def modify_mf_sip(self, sip_id: str, amount: float = None, 
                     status: str = None, instalments: int = None,
                     frequency: str = None, instalment_day: int = None) -> str:
        """Modify mutual fund SIP."""
        data = {}
        if amount:
            data["amount"] = amount
        if status:
            data["status"] = status
        if instalments:
            data["instalments"] = instalments
        if frequency:
            data["frequency"] = frequency
        if instalment_day:
            data["instalment_day"] = instalment_day
        
        result = self._request("PUT", f"/mf/sips/{sip_id}", data=data)
        return result["sip_id"]
    
    def cancel_mf_sip(self, sip_id: str) -> str:
        """Cancel mutual fund SIP."""
        result = self._request("DELETE", f"/mf/sips/{sip_id}")
        return result["sip_id"]
    
    def mf_holdings(self) -> List[Dict[str, Any]]:
        """Get mutual fund holdings."""
        return self._request("GET", "/mf/holdings")
    
    def mf_instruments(self) -> List[Dict[str, Any]]:
        """Get mutual fund instruments."""
        response = self.session.get(
            f"{self.base_url}/mf/instruments", 
            timeout=config.timeout
        )
        response.raise_for_status()
        
        # Parse CSV data for MF instruments
        import io
        df = pd.read_csv(io.StringIO(response.text))
        return df.to_dict('records')
    
    # GTT (Good Till Triggered) Methods
    def get_gtts(self) -> List[Dict[str, Any]]:
        """Get list of GTT orders."""
        return self._request("GET", "/gtt/triggers")
    
    def get_gtt(self, trigger_id: str) -> Dict[str, Any]:
        """Get specific GTT order details."""
        return self._request("GET", f"/gtt/triggers/{trigger_id}")
    
    def place_gtt(self, trigger_type: str, tradingsymbol: str, exchange: str,
                 trigger_values: List[float], last_price: float, 
                 orders: List[Dict[str, Any]]) -> str:
        """Place GTT order."""
        # Validate trigger type
        if trigger_type not in ["single", "two-leg"]:
            raise ValueError("Invalid trigger_type. Must be 'single' or 'two-leg'")
        
        # Validate trigger values
        if trigger_type == "single" and len(trigger_values) != 1:
            raise ValueError("Single leg GTT must have exactly 1 trigger value")
        elif trigger_type == "two-leg" and len(trigger_values) != 2:
            raise ValueError("Two-leg GTT must have exactly 2 trigger values")
        
        condition = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "trigger_values": trigger_values,
            "last_price": last_price
        }
        
        # Validate and format orders
        gtt_orders = []
        for order in orders:
            required_fields = ["transaction_type", "quantity", "order_type", "product", "price"]
            for field in required_fields:
                if field not in order:
                    raise ValueError(f"Missing required field '{field}' in GTT order")
            
            gtt_orders.append({
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "transaction_type": order["transaction_type"],
                "quantity": int(order["quantity"]),
                "order_type": order["order_type"],
                "product": order["product"],
                "price": float(order["price"])
            })
        
        data = {
            "condition": json.dumps(condition),
            "orders": json.dumps(gtt_orders),
            "type": trigger_type
        }
        
        result = self._request("POST", "/gtt/triggers", data=data)
        return result["trigger_id"]
    
    def modify_gtt(self, trigger_id: str, trigger_type: str, tradingsymbol: str, 
                  exchange: str, trigger_values: List[float], last_price: float,
                  orders: List[Dict[str, Any]]) -> str:
        """Modify GTT order."""
        # Use same validation logic as place_gtt
        if trigger_type not in ["single", "two-leg"]:
            raise ValueError("Invalid trigger_type. Must be 'single' or 'two-leg'")
        
        condition = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "trigger_values": trigger_values,
            "last_price": last_price
        }
        
        gtt_orders = []
        for order in orders:
            gtt_orders.append({
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "transaction_type": order["transaction_type"],
                "quantity": int(order["quantity"]),
                "order_type": order["order_type"],
                "product": order["product"],
                "price": float(order["price"])
            })
        
        data = {
            "condition": json.dumps(condition),
            "orders": json.dumps(gtt_orders),
            "type": trigger_type
        }
        
        result = self._request("PUT", f"/gtt/triggers/{trigger_id}", data=data)
        return result["trigger_id"]
    
    def delete_gtt(self, trigger_id: str) -> str:
        """Delete GTT order."""
        result = self._request("DELETE", f"/gtt/triggers/{trigger_id}")
        return result["trigger_id"]
    
    # Market data and analysis methods
    def trigger_range(self, transaction_type: str, instruments: List[str]) -> Dict[str, Any]:
        """Get trigger range for Cover Orders."""
        params = {"i": instruments}
        return self._request("GET", f"/instruments/trigger_range/{transaction_type.lower()}", params=params)
    
    # Margin calculation methods
    def order_margins(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate margins for order list."""
        # Send as JSON body
        import json
        headers = {
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3",
            "Content-Type": "application/json"
        }
        
        response = self.session.post(
            f"{self.base_url}/margins/orders",
            headers=headers,
            data=json.dumps(orders),
            timeout=config.timeout
        )
        
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "error":
            raise APIError(
                result.get("message", "Unknown API error"),
                result.get("error_type"),
                response.status_code
            )
        
        return result.get("data", result)
    
    def basket_order_margins(self, orders: List[Dict[str, Any]], 
                           consider_positions: bool = True, 
                           mode: str = None) -> Dict[str, Any]:
        """Calculate total margins for basket of orders."""
        import json
        headers = {
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3",
            "Content-Type": "application/json"
        }
        
        params = {
            "consider_positions": consider_positions
        }
        if mode:
            params["mode"] = mode
        
        response = self.session.post(
            f"{self.base_url}/margins/basket",
            headers=headers,
            data=json.dumps(orders),
            params=params,
            timeout=config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result.get("data", result)
    
    def get_virtual_contract_note(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate charges for orders."""
        import json
        headers = {
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "X-Kite-Version": "3",
            "Content-Type": "application/json"
        }
        
        response = self.session.post(
            f"{self.base_url}/charges/orders",
            headers=headers,
            data=json.dumps(orders),
            timeout=config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result.get("data", result)
    
    # Session management methods
    def login_url(self) -> str:
        """Get login URL for authentication."""
        return f"https://kite.zerodha.com/connect/login?api_key={self.api_key}"
    
    def renew_access_token(self, refresh_token: str, api_secret: str) -> Dict[str, str]:
        """Renew access token using refresh token."""
        checksum = hashlib.sha256(
            f"{self.api_key}{refresh_token}{api_secret}".encode()
        ).hexdigest()
        
        data = {
            "api_key": self.api_key,
            "refresh_token": refresh_token,
            "checksum": checksum
        }
        
        result = self._request("POST", "/session/refresh_token", data=data)
        if "access_token" in result:
            self.access_token = result["access_token"]
        return result
    
    def invalidate_refresh_token(self, refresh_token: str) -> bool:
        """Invalidate refresh token."""
        try:
            data = {"refresh_token": refresh_token}
            self._request("DELETE", "/session/refresh_token", data=data)
            return True
        except APIError:
            return False
    
    # Additional utility methods
    def set_session_expiry_hook(self, method: callable) -> None:
        """Set callback for session expiry."""
        self._session_expiry_hook = method
    
    # Market segments margins
    # F&O (Futures & Options) Methods
    def get_option_chain(self, tradingsymbol: str, exchange: str = "NFO") -> Dict[str, Any]:
        """Get option chain for F&O instruments."""
        params = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange
        }
        return self._request("GET", "/instruments/option_chain", params=params)
    
    def get_fo_instruments(self) -> List[Dict[str, Any]]:
        """Get F&O instruments from NFO/BFO/CDS/MCX."""
        exchanges = ["NFO", "BFO", "CDS", "MCX"]
        all_instruments = []
        
        for exchange in exchanges:
            try:
                response = self.session.get(
                    f"{self.base_url}/instruments/{exchange}",
                    timeout=config.timeout
                )
                response.raise_for_status()
                
                # Parse CSV data
                import io
                df = pd.read_csv(io.StringIO(response.text))
                df['exchange'] = exchange
                all_instruments.extend(df.to_dict('records'))
            except Exception as e:
                print(f"Failed to fetch {exchange} instruments: {e}")
                continue
        
        return all_instruments
    
    def get_expiry_dates(self, tradingsymbol: str, exchange: str = "NFO") -> List[str]:
        """Get expiry dates for F&O symbol."""
        instruments = self.get_fo_instruments()
        expiries = set()
        
        for inst in instruments:
            if (inst.get('name', '').upper() == tradingsymbol.upper() and 
                inst.get('exchange', '').upper() == exchange.upper() and
                inst.get('expiry')):
                expiries.add(inst['expiry'])
        
        return sorted(list(expiries))
    
    def get_strike_prices(self, tradingsymbol: str, expiry: str, 
                         exchange: str = "NFO") -> Dict[str, List[float]]:
        """Get available strike prices for options."""
        instruments = self.get_fo_instruments()
        strikes = {'CE': set(), 'PE': set()}
        
        for inst in instruments:
            if (inst.get('name', '').upper() == tradingsymbol.upper() and
                inst.get('exchange', '').upper() == exchange.upper() and
                inst.get('expiry') == expiry and
                inst.get('instrument_type') in ['CE', 'PE']):
                strikes[inst['instrument_type']].add(inst.get('strike', 0))
        
        return {
            'CE': sorted(list(strikes['CE'])),
            'PE': sorted(list(strikes['PE']))
        }
    
    def place_fo_order(self, tradingsymbol: str, exchange: str, 
                      transaction_type: str, quantity: int, 
                      product: str = "NRML", order_type: str = "MARKET",
                      price: float = 0, trigger_price: float = 0, 
                      **kwargs) -> str:
        """Place F&O order with appropriate validations."""
        
        # Validate F&O exchanges
        if exchange.upper() not in ["NFO", "BFO", "CDS", "MCX"]:
            raise ValueError(f"Invalid F&O exchange: {exchange}. Use NFO/BFO/CDS/MCX")
        
        # Validate F&O products
        if product not in ["NRML", "MIS"]:
            raise ValueError(f"Invalid F&O product: {product}. Use NRML or MIS")
        
        # Place order using standard method
        return self.place_order(
            variety="regular",
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=product,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            **kwargs
        )
