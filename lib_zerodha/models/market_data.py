"""Market data models."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import OHLC, DepthItem


@dataclass
class Quote:
    """Real-time quote data."""
    instrument_token: int
    timestamp: Optional[datetime] = None
    last_price: float = 0.0
    last_quantity: int = 0
    average_price: float = 0.0
    volume: int = 0
    buy_quantity: int = 0
    sell_quantity: int = 0
    ohlc: Optional[OHLC] = None
    net_change: float = 0.0
    oi: Optional[int] = None  # Open Interest for F&O
    oi_day_high: Optional[int] = None
    oi_day_low: Optional[int] = None
    lower_circuit_limit: Optional[float] = None
    upper_circuit_limit: Optional[float] = None
    depth: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
    
    @property
    def change_percent(self) -> float:
        """Calculate percentage change."""
        if self.ohlc and self.ohlc.close > 0:
            return ((self.last_price - self.ohlc.close) / self.ohlc.close) * 100
        return 0.0
    
    @property
    def is_upper_circuit(self) -> bool:
        """Check if price hit upper circuit."""
        return (self.upper_circuit_limit is not None and 
                abs(self.last_price - self.upper_circuit_limit) < 0.01)
    
    @property
    def is_lower_circuit(self) -> bool:
        """Check if price hit lower circuit."""
        return (self.lower_circuit_limit is not None and 
                abs(self.last_price - self.lower_circuit_limit) < 0.01)


@dataclass
class HistoricalData:
    """Historical candle data."""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    oi: Optional[int] = None  # Open Interest for F&O
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.date, str):
            self.date = datetime.fromisoformat(self.date)
    
    @property
    def ohlc(self) -> OHLC:
        """Get OHLC object."""
        return OHLC(self.open, self.high, self.low, self.close)
    
    @property
    def body_size(self) -> float:
        """Calculate candle body size."""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Calculate upper shadow size."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Calculate lower shadow size."""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish."""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """Check if candle is doji."""
        return abs(self.close - self.open) < (self.high - self.low) * 0.1


@dataclass
class Tick:
    """Real-time tick data."""
    instrument_token: int
    timestamp: datetime
    last_price: float
    volume: int
    average_price: float
    oi: Optional[int] = None
    ohlc: Optional[OHLC] = None
    depth: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))