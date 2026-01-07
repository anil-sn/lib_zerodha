"""Optimized data models for Kite Connect API responses."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
from decimal import Decimal
import pandas as pd

@dataclass
class OHLC:
    """OHLC data structure optimized for processing."""
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = 0
    
    def to_dict(self) -> Dict[str, Union[float, int]]:
        return {
            'open': self.open,
            'high': self.high, 
            'low': self.low,
            'close': self.close,
            'volume': self.volume or 0
        }

@dataclass
class DepthItem:
    """Market depth item."""
    price: float
    quantity: int
    orders: int = 0

@dataclass
class Quote:
    """Real-time quote data optimized for analysis."""
    instrument_token: int
    timestamp: datetime
    last_price: float
    
    # OHLC data
    ohlc: OHLC
    
    # Volume data
    volume: int = 0
    average_price: float = 0.0
    
    # Market depth
    depth: Dict[str, List[DepthItem]] = field(default_factory=lambda: {"buy": [], "sell": []})
    
    # Additional fields
    oi: int = 0  # Open Interest
    oi_day_high: int = 0
    oi_day_low: int = 0
    
    def to_pandas_row(self) -> Dict[str, Any]:
        """Convert to pandas-compatible row."""
        return {
            'instrument_token': self.instrument_token,
            'timestamp': self.timestamp,
            'ltp': self.last_price,
            'open': self.ohlc.open,
            'high': self.ohlc.high,
            'low': self.ohlc.low,
            'close': self.ohlc.close,
            'volume': self.volume,
            'avg_price': self.average_price,
            'oi': self.oi
        }

@dataclass
class Instrument:
    """Instrument master data."""
    instrument_token: int
    exchange_token: int
    tradingsymbol: str
    name: str
    last_price: float
    expiry: Optional[datetime]
    strike: float
    tick_size: float
    lot_size: int
    instrument_type: str
    segment: str
    exchange: str
    
    def __hash__(self) -> int:
        return hash(self.instrument_token)
    
    def is_equity(self) -> bool:
        return self.instrument_type == "EQ"
    
    def is_derivative(self) -> bool:
        return self.instrument_type in ["CE", "PE", "FUT"]

@dataclass
class Position:
    """Portfolio position data."""
    tradingsymbol: str
    exchange: str
    instrument_token: int
    product: str
    quantity: int
    overnight_quantity: int
    multiplier: int
    average_price: float
    close_price: float
    last_price: float
    value: float
    pnl: float
    m2m: float
    unrealised: float
    realised: float
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0

@dataclass
class Order:
    """Order data structure."""
    order_id: str
    parent_order_id: Optional[str]
    exchange: str
    tradingsymbol: str
    instrument_token: int
    transaction_type: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT/SL/SL-M
    product: str  # MIS/CNC/NRML
    quantity: int
    disclosed_quantity: int
    price: float
    trigger_price: float
    average_price: float
    filled_quantity: int
    pending_quantity: int
    cancelled_quantity: int
    status: str
    status_message: str
    order_timestamp: datetime
    exchange_timestamp: Optional[datetime]
    variety: str
    validity: str
    tag: Optional[str]
    
    @property
    def is_complete(self) -> bool:
        return self.status == "COMPLETE"
    
    @property
    def is_pending(self) -> bool:
        return self.status in ["OPEN", "TRIGGER PENDING"]

@dataclass
class Trade:
    """Trade/fill data structure."""
    trade_id: str
    order_id: str
    exchange: str
    tradingsymbol: str
    instrument_token: int
    transaction_type: str
    product: str
    quantity: int
    average_price: float
    fill_timestamp: datetime
    exchange_timestamp: datetime

@dataclass
class Holding:
    """Holdings data structure."""
    tradingsymbol: str
    exchange: str
    instrument_token: int
    isin: str
    product: str
    quantity: int
    t1_quantity: int
    realised_quantity: int
    authorised_quantity: int
    authorised_date: Optional[datetime]
    opening_quantity: int
    collateral_quantity: int
    collateral_type: str
    discrepancy: bool
    average_price: float
    last_price: float
    close_price: float
    pnl: float
    day_change: float
    day_change_percentage: float

@dataclass
class MarginInfo:
    """Margin information."""
    equity: Dict[str, float] = field(default_factory=dict)
    commodity: Dict[str, float] = field(default_factory=dict)
    
    @property
    def total_available(self) -> float:
        equity_available = self.equity.get("available", {}).get("live_balance", 0)
        commodity_available = self.commodity.get("available", {}).get("live_balance", 0)
        return equity_available + commodity_available

@dataclass
class Portfolio:
    """Complete portfolio data structure."""
    positions: List[Position] = field(default_factory=list)
    holdings: List[Holding] = field(default_factory=list)
    margin: Optional[MarginInfo] = None
    
    def to_dataframe(self, data_type: str = "positions") -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        if data_type == "positions":
            return pd.DataFrame([pos.__dict__ for pos in self.positions])
        elif data_type == "holdings":
            return pd.DataFrame([holding.__dict__ for holding in self.holdings])
        else:
            raise ValueError("data_type must be 'positions' or 'holdings'")
    
    @property
    def total_pnl(self) -> float:
        return sum(pos.pnl for pos in self.positions)
    
    @property
    def total_value(self) -> float:
        return sum(pos.value for pos in self.positions)

# Historical data structures
@dataclass
class HistoricalData:
    """Historical OHLCV data optimized for pandas processing."""
    instrument_token: int
    interval: str
    data: pd.DataFrame  # Columns: [date, open, high, low, close, volume, oi]
    
    def __post_init__(self):
        """Ensure proper data types for analysis."""
        if not self.data.empty:
            # Ensure datetime index
            if 'date' in self.data.columns:
                self.data['date'] = pd.to_datetime(self.data['date'])
                self.data.set_index('date', inplace=True)
            
            # Ensure numeric types
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'oi']
            for col in numeric_cols:
                if col in self.data.columns:
                    self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
    
    def get_latest(self, count: int = 1) -> pd.DataFrame:
        """Get latest N records."""
        return self.data.tail(count)
    
    def add_technical_indicators(self) -> 'HistoricalData':
        """Add common technical indicators."""
        # Simple Moving Averages
        self.data['sma_20'] = self.data['close'].rolling(20).mean()
        self.data['sma_50'] = self.data['close'].rolling(50).mean()
        
        # RSI
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume Moving Average
        self.data['volume_sma_20'] = self.data['volume'].rolling(20).mean()
        
        return self


@dataclass
class Trade:
    """Trade information."""
    trade_id: str
    order_id: str
    exchange: str
    tradingsymbol: str
    instrument_token: int
    transaction_type: str
    product: str
    average_price: float
    quantity: int
    exchange_timestamp: datetime = None
    
    def __post_init__(self):
        """Post initialization processing."""
        if isinstance(self.exchange_timestamp, str):
            self.exchange_timestamp = pd.to_datetime(self.exchange_timestamp)
    
    def to_pandas(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series({
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "exchange": self.exchange,
            "tradingsymbol": self.tradingsymbol,
            "instrument_token": self.instrument_token,
            "transaction_type": self.transaction_type,
            "product": self.product,
            "average_price": self.average_price,
            "quantity": self.quantity,
            "exchange_timestamp": self.exchange_timestamp
        })


@dataclass
class GTTTrigger:
    """GTT (Good Till Triggered) trigger information."""
    id: int
    user_id: str
    type: str  # single, two-leg
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    status: str  # active, triggered, disabled, expired, cancelled, rejected
    condition: Dict[str, Any]  # Exchange, tradingsymbol, trigger_values, last_price
    orders: List[Dict[str, Any]]
    
    def __post_init__(self):
        """Post initialization processing."""
        if isinstance(self.created_at, str):
            self.created_at = pd.to_datetime(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = pd.to_datetime(self.updated_at)
        if isinstance(self.expires_at, str):
            self.expires_at = pd.to_datetime(self.expires_at)
    
    def to_pandas(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series({
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "condition": self.condition,
            "orders": self.orders
        })


@dataclass
class MFHolding:
    """Mutual Fund holding information."""
    folio: str
    fund: str
    tradingsymbol: str
    average_price: float
    last_price: float
    last_price_date: Optional[datetime] = None
    pnl: float = 0.0
    quantity: float = 0.0
    
    def __post_init__(self):
        """Post initialization processing."""
        if isinstance(self.last_price_date, str):
            self.last_price_date = pd.to_datetime(self.last_price_date)
    
    def to_pandas(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series({
            "folio": self.folio,
            "fund": self.fund,
            "tradingsymbol": self.tradingsymbol,
            "average_price": self.average_price,
            "last_price": self.last_price,
            "last_price_date": self.last_price_date,
            "pnl": self.pnl,
            "quantity": self.quantity
        })


@dataclass
class MarginInfo:
    """Margin calculation information."""
    equity: Optional[Dict[str, float]] = None
    commodity: Optional[Dict[str, float]] = None
    
    def to_pandas(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        data = []
        if self.equity:
            for key, value in self.equity.items():
                data.append({"segment": "equity", "type": key, "amount": value})
        if self.commodity:
            for key, value in self.commodity.items():
                data.append({"segment": "commodity", "type": key, "amount": value})
        return pd.DataFrame(data)


@dataclass
class FOInstrument:
    """F&O Instrument information."""
    instrument_token: int
    exchange_token: int
    tradingsymbol: str
    name: str
    last_price: float
    expiry: Optional[datetime] = None
    strike: float = 0.0
    tick_size: float = 0.01
    lot_size: int = 1
    instrument_type: str = ""  # CE, PE, FUT
    segment: str = ""  # NFO, BFO, CDS, MCX
    exchange: str = ""
    
    def __post_init__(self):
        """Post initialization processing."""
        if isinstance(self.expiry, str):
            self.expiry = pd.to_datetime(self.expiry)
    
    @property
    def is_option(self) -> bool:
        """Check if instrument is an option."""
        return self.instrument_type in ['CE', 'PE']
    
    @property
    def is_future(self) -> bool:
        """Check if instrument is a future."""
        return self.instrument_type == 'FUT'
    
    @property
    def days_to_expiry(self) -> Optional[int]:
        """Calculate days to expiry."""
        if self.expiry:
            return (self.expiry.date() - datetime.now().date()).days
        return None
    
    def to_pandas(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series({
            "instrument_token": self.instrument_token,
            "exchange_token": self.exchange_token,
            "tradingsymbol": self.tradingsymbol,
            "name": self.name,
            "last_price": self.last_price,
            "expiry": self.expiry,
            "strike": self.strike,
            "tick_size": self.tick_size,
            "lot_size": self.lot_size,
            "instrument_type": self.instrument_type,
            "segment": self.segment,
            "exchange": self.exchange,
            "is_option": self.is_option,
            "is_future": self.is_future,
            "days_to_expiry": self.days_to_expiry
        })


@dataclass
class OptionChain:
    """Option chain data for F&O analysis."""
    underlying: str
    expiry: datetime
    strikes: Dict[float, Dict[str, Any]]  # {strike: {"CE": {...}, "PE": {...}}}
    spot_price: float
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_atm_strike(self) -> float:
        """Get At-The-Money strike price."""
        strikes = list(self.strikes.keys())
        return min(strikes, key=lambda x: abs(x - self.spot_price))
    
    def get_itm_otm_strikes(self, option_type: str = "CE", count: int = 5) -> Dict[str, List[float]]:
        """Get In-The-Money and Out-Of-The-Money strikes."""
        strikes = sorted(self.strikes.keys())
        atm = self.get_atm_strike()
        atm_index = strikes.index(atm)
        
        if option_type == "CE":
            itm = strikes[:atm_index][-count:] if atm_index > 0 else []
            otm = strikes[atm_index+1:atm_index+1+count]
        else:  # PE
            itm = strikes[atm_index+1:atm_index+1+count]
            otm = strikes[:atm_index][-count:] if atm_index > 0 else []
        
        return {"ITM": itm, "OTM": otm, "ATM": [atm]}
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert option chain to pandas DataFrame."""
        data = []
        for strike, options in self.strikes.items():
            row = {"strike": strike, "spot_price": self.spot_price}
            for opt_type in ['PE', 'CE']:
                if opt_type in options:
                    opt_data = options[opt_type]
                    for key, value in opt_data.items():
                        row[f"{opt_type.lower()}_{key}"] = value
            data.append(row)
        
        df = pd.DataFrame(data)
        df['expiry'] = self.expiry
        df['underlying'] = self.underlying
        return df
