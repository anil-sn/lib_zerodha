"""Order parameter validation."""

import re
from typing import Optional, Union

from ..exceptions import ValidationError
from .order_types import (
    OrderType, ProductType, TransactionType, Exchange, Validity,
    VALID_COMBINATIONS
)


class OrderValidator:
    """Validates order parameters before placement."""
    
    # Trading symbol patterns
    EQUITY_PATTERN = re.compile(r'^[A-Z0-9&-]+$')
    FUTURES_PATTERN = re.compile(r'^[A-Z0-9&-]+\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)FUT$')
    OPTIONS_PATTERN = re.compile(r'^[A-Z0-9&-]+\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d+(CE|PE)$')
    
    def validate_order(self,
                      tradingsymbol: str,
                      exchange: str,
                      transaction_type: str,
                      quantity: int,
                      order_type: str,
                      product: str,
                      price: Optional[float] = None,
                      trigger_price: Optional[float] = None,
                      disclosed_quantity: Optional[int] = None) -> bool:
        """Validate all order parameters.
        
        Args:
            tradingsymbol: Trading symbol
            exchange: Exchange name
            transaction_type: BUY/SELL
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            product: Product type (CNC, MIS, NRML)
            price: Order price (for limit orders)
            trigger_price: Trigger price (for SL orders)
            disclosed_quantity: Disclosed quantity (for iceberg orders)
            
        Returns:
            True if all validations pass
            
        Raises:
            ValidationError: If any validation fails
        """
        # Validate trading symbol
        self.validate_tradingsymbol(tradingsymbol, exchange)
        
        # Validate exchange
        self.validate_exchange(exchange)
        
        # Validate transaction type
        self.validate_transaction_type(transaction_type)
        
        # Validate quantity
        self.validate_quantity(quantity)
        
        # Validate order type
        self.validate_order_type(order_type)
        
        # Validate product type
        self.validate_product_type(product)
        
        # Validate order type and product combination
        self.validate_order_product_combination(order_type, product)
        
        # Validate price parameters
        self.validate_price_parameters(order_type, price, trigger_price)
        
        # Validate disclosed quantity
        if disclosed_quantity is not None:
            self.validate_disclosed_quantity(disclosed_quantity, quantity)
        
        return True
    
    def validate_tradingsymbol(self, tradingsymbol: str, exchange: str) -> bool:
        """Validate trading symbol format.
        
        Args:
            tradingsymbol: Trading symbol to validate
            exchange: Exchange for context
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If symbol format is invalid
        """
        if not tradingsymbol or not isinstance(tradingsymbol, str):
            raise ValidationError("Trading symbol must be a non-empty string")
        
        if len(tradingsymbol) > 50:
            raise ValidationError("Trading symbol too long (max 50 characters)")
        
        # Exchange-specific validation
        if exchange in ['NSE', 'BSE']:
            if not self.EQUITY_PATTERN.match(tradingsymbol):
                raise ValidationError(f"Invalid equity symbol format: {tradingsymbol}")
        elif exchange in ['NFO', 'BFO', 'CDS', 'MCX']:
            if (not self.FUTURES_PATTERN.match(tradingsymbol) and 
                not self.OPTIONS_PATTERN.match(tradingsymbol)):
                raise ValidationError(f"Invalid F&O symbol format: {tradingsymbol}")
        
        return True
    
    def validate_exchange(self, exchange: str) -> bool:
        """Validate exchange.
        
        Args:
            exchange: Exchange to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If exchange is invalid
        """
        valid_exchanges = [e.value for e in Exchange]
        if exchange not in valid_exchanges:
            raise ValidationError(f"Invalid exchange: {exchange}. Valid: {valid_exchanges}")
        
        return True
    
    def validate_transaction_type(self, transaction_type: str) -> bool:
        """Validate transaction type.
        
        Args:
            transaction_type: Transaction type to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If transaction type is invalid
        """
        valid_types = [t.value for t in TransactionType]
        if transaction_type.upper() not in valid_types:
            raise ValidationError(f"Invalid transaction type: {transaction_type}. Valid: {valid_types}")
        
        return True
    
    def validate_quantity(self, quantity: int) -> bool:
        """Validate order quantity.
        
        Args:
            quantity: Quantity to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If quantity is invalid
        """
        if not isinstance(quantity, int):
            raise ValidationError("Quantity must be an integer")
            
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        return True
    
    def validate_order_type(self, order_type: str) -> bool:
        """Validate order type.
        
        Args:
            order_type: Order type to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If order type is invalid
        """
        valid_types = [t.value for t in OrderType]
        if order_type.upper() not in valid_types:
            raise ValidationError(f"Invalid order type: {order_type}. Valid: {valid_types}")
        
        return True
    
    def validate_product_type(self, product: str) -> bool:
        """Validate product type.
        
        Args:
            product: Product type to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If product type is invalid
        """
        valid_products = [p.value for p in ProductType]
        if product.upper() not in valid_products:
            raise ValidationError(f"Invalid product type: {product}. Valid: {valid_products}")
        
        return True
    
    def validate_order_product_combination(self, order_type: str, product: str) -> bool:
        """Validate order type and product combination.
        
        Args:
            order_type: Order type
            product: Product type
            
        Returns:
            True if valid combination
            
        Raises:
            ValidationError: If combination is invalid
        """
        try:
            order_enum = OrderType(order_type.upper())
            product_enum = ProductType(product.upper())
        except ValueError as e:
            raise ValidationError(f"Invalid enum value: {str(e)}")
        
        valid_products = VALID_COMBINATIONS.get(order_enum, [])
        if product_enum not in valid_products:
            raise ValidationError(
                f"Invalid combination: {order_type} order with {product} product"
            )
        
        return True
    
    def validate_price_parameters(self,
                                 order_type: str,
                                 price: Optional[float] = None,
                                 trigger_price: Optional[float] = None) -> bool:
        """Validate price and trigger price parameters.
        
        Args:
            order_type: Order type
            price: Order price
            trigger_price: Trigger price
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If price parameters are invalid
        """
        order_type = order_type.upper()
        
        # LIMIT orders must have price
        if order_type == 'LIMIT' and price is None:
            raise ValidationError("LIMIT orders must specify price")
        
        # SL orders must have trigger_price
        if order_type in ['SL', 'SL-M'] and trigger_price is None:
            raise ValidationError("Stop loss orders must specify trigger_price")
        
        # MARKET orders should not have price
        if order_type == 'MARKET' and price is not None:
            raise ValidationError("MARKET orders should not specify price")
        
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than 0")
            
        if trigger_price is not None and trigger_price <= 0:
            raise ValidationError("Trigger price must be greater than 0")
        
        return True
    
    def validate_disclosed_quantity(self, disclosed_quantity: int, total_quantity: int) -> bool:
        """Validate disclosed quantity for iceberg orders.
        
        Args:
            disclosed_quantity: Disclosed quantity
            total_quantity: Total order quantity
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If disclosed quantity is invalid
        """
        if not isinstance(disclosed_quantity, int):
            raise ValidationError("Disclosed quantity must be an integer")
            
        if disclosed_quantity <= 0:
            raise ValidationError("Disclosed quantity must be greater than 0")
        
        if disclosed_quantity > total_quantity:
            raise ValidationError("Disclosed quantity cannot exceed total quantity")
        
        return True