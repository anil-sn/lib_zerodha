"""Order placement and management for Kite Connect API."""

from typing import Dict, List, Optional, Union, Any
import requests
from datetime import datetime

from ..config import config
from ..exceptions import APIError, NetworkError, ValidationError, OrderError
from .order_types import OrderType, ProductType, TransactionType, Variety
from .order_validation import OrderValidator


class KiteOrders:
    """Handles order placement, modification, and management."""
    
    def __init__(self, session: requests.Session, get_auth_headers: callable):
        """Initialize order management.
        
        Args:
            session: Requests session for API calls
            get_auth_headers: Function to get authentication headers
        """
        self.session = session
        self.get_auth_headers = get_auth_headers
        self.validator = OrderValidator()
    
    def place_order(self,
                   tradingsymbol: str,
                   exchange: str,
                   transaction_type: Union[str, TransactionType],
                   quantity: int,
                   order_type: Union[str, OrderType],
                   product: Union[str, ProductType],
                   price: Optional[float] = None,
                   trigger_price: Optional[float] = None,
                   disclosed_quantity: Optional[int] = None,
                   validity: str = "DAY",
                   variety: Union[str, Variety] = Variety.REGULAR,
                   tag: Optional[str] = None) -> str:
        """Place a new order.
        
        Args:
            tradingsymbol: Trading symbol (e.g., 'RELIANCE', 'NIFTY2470020000CE')
            exchange: Exchange (NSE, BSE, NFO, BFO, CDS, MCX)
            transaction_type: BUY or SELL
            quantity: Quantity to trade
            order_type: MARKET, LIMIT, SL, SL-M
            product: CNC, MIS, NRML
            price: Price for limit orders
            trigger_price: Trigger price for SL orders
            disclosed_quantity: Disclosed quantity for iceberg orders
            validity: Order validity (DAY, IOC)
            variety: Order variety (regular, amo, co, iceberg)
            tag: Optional tag for order identification
            
        Returns:
            Order ID
            
        Raises:
            ValidationError: If order parameters are invalid
            OrderError: If order placement fails
            NetworkError: If network request fails
        """
        # Convert enums to strings if needed
        transaction_type = str(transaction_type) if hasattr(transaction_type, 'value') else transaction_type
        order_type = str(order_type) if hasattr(order_type, 'value') else order_type
        product = str(product) if hasattr(product, 'value') else product
        variety = str(variety) if hasattr(variety, 'value') else variety
        
        # Validate order parameters
        self.validator.validate_order(
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product=product,
            price=price,
            trigger_price=trigger_price
        )
        
        # Prepare order data
        order_data = {
            'tradingsymbol': tradingsymbol,
            'exchange': exchange,
            'transaction_type': transaction_type.upper(),
            'quantity': quantity,
            'order_type': order_type.upper(),
            'product': product.upper(),
            'validity': validity.upper()
        }
        
        # Add optional parameters
        if price is not None:
            order_data['price'] = price
        if trigger_price is not None:
            order_data['trigger_price'] = trigger_price
        if disclosed_quantity is not None:
            order_data['disclosed_quantity'] = disclosed_quantity
        if tag:
            order_data['tag'] = tag
        
        try:
            response = self.session.post(
                f"{config.BASE_URL}/orders/{variety}",
                headers=self.get_auth_headers(),
                data=order_data,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(
                    result.get('message', 'Order placement failed'),
                    result.get('error_type')
                )
            
            return result.get('data', {}).get('order_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error during order placement: {str(e)}")
    
    def modify_order(self,
                    order_id: str,
                    quantity: Optional[int] = None,
                    price: Optional[float] = None,
                    trigger_price: Optional[float] = None,
                    order_type: Optional[Union[str, OrderType]] = None,
                    validity: Optional[str] = None,
                    disclosed_quantity: Optional[int] = None,
                    variety: Union[str, Variety] = Variety.REGULAR) -> str:
        """Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
            order_type: New order type
            validity: New validity
            disclosed_quantity: New disclosed quantity
            variety: Order variety
            
        Returns:
            Order ID
            
        Raises:
            OrderError: If order modification fails
            NetworkError: If network request fails
        """
        variety = str(variety) if hasattr(variety, 'value') else variety
        
        # Prepare modification data (only include non-None values)
        modify_data = {}
        if quantity is not None:
            modify_data['quantity'] = quantity
        if price is not None:
            modify_data['price'] = price
        if trigger_price is not None:
            modify_data['trigger_price'] = trigger_price
        if order_type is not None:
            order_type = str(order_type) if hasattr(order_type, 'value') else order_type
            modify_data['order_type'] = order_type.upper()
        if validity is not None:
            modify_data['validity'] = validity.upper()
        if disclosed_quantity is not None:
            modify_data['disclosed_quantity'] = disclosed_quantity
        
        if not modify_data:
            raise ValidationError("At least one parameter must be provided for modification")
        
        try:
            response = self.session.put(
                f"{config.BASE_URL}/orders/{variety}/{order_id}",
                headers=self.get_auth_headers(),
                data=modify_data,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(
                    result.get('message', 'Order modification failed'),
                    result.get('error_type')
                )
            
            return result.get('data', {}).get('order_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error during order modification: {str(e)}")
    
    def cancel_order(self, order_id: str, variety: Union[str, Variety] = Variety.REGULAR) -> str:
        """Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            variety: Order variety
            
        Returns:
            Order ID
            
        Raises:
            OrderError: If order cancellation fails
            NetworkError: If network request fails
        """
        variety = str(variety) if hasattr(variety, 'value') else variety
        
        try:
            response = self.session.delete(
                f"{config.BASE_URL}/orders/{variety}/{order_id}",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(
                    result.get('message', 'Order cancellation failed'),
                    result.get('error_type')
                )
            
            return result.get('data', {}).get('order_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error during order cancellation: {str(e)}")
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders for the day.
        
        Returns:
            List of order dictionaries
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{config.BASE_URL}/orders",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch orders'),
                    result.get('error_type')
                )
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching orders: {str(e)}")
    
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get order history/audit trail.
        
        Args:
            order_id: Order ID to get history for
            
        Returns:
            List of order history entries
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{config.BASE_URL}/orders/{order_id}",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch order history'),
                    result.get('error_type')
                )
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching order history: {str(e)}")
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all executed trades for the day.
        
        Returns:
            List of trade dictionaries
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{config.BASE_URL}/trades",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch trades'),
                    result.get('error_type')
                )
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching trades: {str(e)}")
    
    def get_order_trades(self, order_id: str) -> List[Dict[str, Any]]:
        """Get trades for a specific order.
        
        Args:
            order_id: Order ID to get trades for
            
        Returns:
            List of trade dictionaries for the order
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{config.BASE_URL}/orders/{order_id}/trades",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch order trades'),
                    result.get('error_type')
                )
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching order trades: {str(e)}")