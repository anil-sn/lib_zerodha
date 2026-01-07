"""Order type definitions and enums."""

from enum import Enum
from typing import Dict, Any


class OrderType(Enum):
    """Order types supported by Kite Connect."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss
    SL_M = "SL-M"  # Stop Loss Market
    
    def __str__(self):
        return self.value


class TransactionType(Enum):
    """Transaction types."""
    BUY = "BUY"
    SELL = "SELL"
    
    def __str__(self):
        return self.value


class ProductType(Enum):
    """Product types for different trading segments."""
    CNC = "CNC"  # Cash and Carry
    MIS = "MIS"  # Margin Intraday Square-off
    NRML = "NRML"  # Normal
    
    def __str__(self):
        return self.value


class Variety(Enum):
    """Order varieties."""
    REGULAR = "regular"
    AMO = "amo"  # After Market Order
    CO = "co"    # Cover Order
    ICEBERG = "iceberg"
    AUCTION = "auction"
    
    def __str__(self):
        return self.value


class Exchange(Enum):
    """Supported exchanges."""
    NSE = "NSE"  # National Stock Exchange
    BSE = "BSE"  # Bombay Stock Exchange
    NFO = "NFO"  # NSE Futures & Options
    BFO = "BFO"  # BSE Futures & Options  
    CDS = "CDS"  # Currency Derivatives
    MCX = "MCX"  # Multi Commodity Exchange
    
    def __str__(self):
        return self.value


class Validity(Enum):
    """Order validity types."""
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    
    def __str__(self):
        return self.value


class OrderStatus(Enum):
    """Order status types."""
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFY_PENDING = "MODIFY PENDING"
    CANCEL_PENDING = "CANCEL PENDING"
    TRIGGER_PENDING = "TRIGGER PENDING"
    
    def __str__(self):
        return self.value


class InstrumentType(Enum):
    """Instrument types."""
    EQ = "EQ"    # Equity
    FUT = "FUT"  # Futures
    CE = "CE"    # Call Option
    PE = "PE"    # Put Option
    
    def __str__(self):
        return self.value


# Order parameter constraints
ORDER_CONSTRAINTS = {
    'quantity': {
        'min': 1,
        'max': 1000000
    },
    'price': {
        'min': 0.01,
        'max': 1000000.0
    },
    'trigger_price': {
        'min': 0.01,
        'max': 1000000.0
    },
    'disclosed_quantity': {
        'min': 1,
        'max': 1000000
    }
}

# Valid combinations of order types and products
VALID_COMBINATIONS = {
    OrderType.MARKET: [ProductType.CNC, ProductType.MIS, ProductType.NRML],
    OrderType.LIMIT: [ProductType.CNC, ProductType.MIS, ProductType.NRML],
    OrderType.SL: [ProductType.MIS, ProductType.NRML],
    OrderType.SL_M: [ProductType.MIS, ProductType.NRML]
}

# Exchange-specific instrument types
EXCHANGE_INSTRUMENTS = {
    Exchange.NSE: [InstrumentType.EQ],
    Exchange.BSE: [InstrumentType.EQ],
    Exchange.NFO: [InstrumentType.FUT, InstrumentType.CE, InstrumentType.PE],
    Exchange.BFO: [InstrumentType.FUT, InstrumentType.CE, InstrumentType.PE],
    Exchange.CDS: [InstrumentType.FUT, InstrumentType.CE, InstrumentType.PE],
    Exchange.MCX: [InstrumentType.FUT, InstrumentType.CE, InstrumentType.PE]
}