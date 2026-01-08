"""Market data models."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import OHLC, DepthItem, Quote


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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoricalData':
        """Create HistoricalData from API response with resilient parsing."""
        from datetime import datetime
        
        # Parse date safely
        date = data.get('date')
        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace(' ', 'T'))
        elif not isinstance(date, datetime):
            date = datetime.now()
        
        return cls(
            date=date,
            open=float(data.get('open', 0.0)),
            high=float(data.get('high', 0.0)),
            low=float(data.get('low', 0.0)),
            close=float(data.get('close', 0.0)),
            volume=int(data.get('volume', 0)),
            oi=data.get('oi')
        )
    
    @property
    def ohlc(self) -> OHLC:
        """Get OHLC object."""
        return OHLC(self.open, self.high, self.low, self.close, self.volume)
    
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
    last_trade_time: Optional[datetime] = None
    exchange_timestamp: Optional[datetime] = None
    mode: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tick':
        """Create Tick from WebSocket data with resilient parsing."""
        from datetime import datetime
        
        # Parse timestamp safely
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace(' ', 'T'))
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
            
        # Parse extra timestamps
        last_trade_time = data.get('last_trade_time')
        if isinstance(last_trade_time, int):
             # Assuming unix timestamp from struct unpack
             # However, Kite sends timestamps as seconds since epoch in binary?
             # Docs say "4 bytes". It is likely Unix timestamp.
             try:
                 last_trade_time = datetime.fromtimestamp(last_trade_time)
             except:
                 last_trade_time = None
                 
        exchange_timestamp = data.get('exchange_timestamp')
        if isinstance(exchange_timestamp, int):
             try:
                 exchange_timestamp = datetime.fromtimestamp(exchange_timestamp)
             except:
                 exchange_timestamp = None
        
        # Handle OHLC if present
        ohlc = None
        if 'ohlc' in data and data['ohlc']:
            ohlc_data = data['ohlc']
            ohlc = OHLC(
                open=ohlc_data.get('open', 0.0),
                high=ohlc_data.get('high', 0.0),
                low=ohlc_data.get('low', 0.0),
                close=ohlc_data.get('close', 0.0),
                volume=data.get('volume', 0)
            )
        
        return cls(
            instrument_token=int(data.get('instrument_token', 0)),
            timestamp=timestamp,
            last_price=float(data.get('last_price', 0.0)),
            volume=int(data.get('volume', 0)),
            average_price=float(data.get('average_price', 0.0)),
            oi=data.get('oi'),
            ohlc=ohlc,
            depth=data.get('depth'),
            last_trade_time=last_trade_time,
            exchange_timestamp=exchange_timestamp,
            mode=data.get('mode')
        )