"""Data processor for handling and aggregating tick data."""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import threading
import pandas as pd
from dataclasses import dataclass, field

from ..models.market_data import Quote, OHLC, HistoricalData

@dataclass
class CandleData:
    """Internal candle data structure for aggregation."""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    tick_count: int = 0
    
    def update_tick(self, price: float, volume: int = 0):
        """Update candle with new tick data."""
        if self.tick_count == 0:
            self.open = price
            self.high = price
            self.low = price
        
        self.close = price
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.volume += volume
        self.tick_count += 1
    
    def to_ohlc(self) -> OHLC:
        """Convert to OHLC data model."""
        return OHLC(
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume
        )

class DataProcessor:
    """Processes and aggregates real-time tick data into candles."""
    
    # Supported intervals (in minutes)
    INTERVALS = {
        '1minute': 1,
        '3minute': 3,
        '5minute': 5,
        '10minute': 10,
        '15minute': 15,
        '30minute': 30,
        '60minute': 60,
        'day': 1440  # 24 * 60
    }
    
    def __init__(self, max_candles_per_interval: int = 1000):
        self.max_candles = max_candles_per_interval
        
        # Data storage: interval -> instrument_token -> candles
        self.candles: Dict[str, Dict[int, deque]] = {
            interval: defaultdict(lambda: deque(maxlen=max_candles_per_interval))
            for interval in self.INTERVALS.keys()
        }
        
        # Current building candles: interval -> instrument_token -> CandleData
        self.current_candles: Dict[str, Dict[int, CandleData]] = {
            interval: defaultdict(CandleData)
            for interval in self.INTERVALS.keys()
        }
        
        # Latest tick data
        self.latest_ticks: Dict[int, Dict[str, Any]] = {}
        
        # Callbacks for candle completion
        self.candle_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Threading lock
        self._lock = threading.RLock()
        
        # Quote cache
        self.quote_cache: Dict[int, Quote] = {}
        self.cache_timestamps: Dict[int, datetime] = {}
        self.cache_ttl = timedelta(seconds=5)  # 5-second cache TTL
    
    def process_tick(self, tick_data: Dict[str, Any]) -> None:
        """Process incoming tick data."""
        with self._lock:
            instrument_token = tick_data.get('instrument_token')
            if not instrument_token:
                return
            
            timestamp = tick_data.get('timestamp', datetime.now())
            last_price = tick_data.get('last_price', 0)
            volume = tick_data.get('volume', 0)
            
            # Update latest tick cache
            self.latest_ticks[instrument_token] = tick_data
            
            # Update quote cache if available
            self._update_quote_cache(tick_data)
            
            # Process for each interval
            for interval_name, interval_minutes in self.INTERVALS.items():
                self._process_tick_for_interval(
                    instrument_token, timestamp, last_price, volume, 
                    interval_name, interval_minutes
                )
    
    def _update_quote_cache(self, tick_data: Dict[str, Any]) -> None:
        """Update quote cache with tick data."""
        instrument_token = tick_data.get('instrument_token')
        timestamp = tick_data.get('timestamp', datetime.now())
        
        # Create quote from tick data
        ohlc_data = tick_data.get('ohlc', {})
        if ohlc_data:
            ohlc = OHLC(
                open=ohlc_data.get('open', tick_data.get('last_price', 0)),
                high=ohlc_data.get('high', tick_data.get('last_price', 0)),
                low=ohlc_data.get('low', tick_data.get('last_price', 0)),
                close=ohlc_data.get('close', tick_data.get('last_price', 0)),
                volume=tick_data.get('volume', 0)
            )
        else:
            # Create OHLC from LTP only
            ltp = tick_data.get('last_price', 0)
            ohlc = OHLC(open=ltp, high=ltp, low=ltp, close=ltp)
        
        quote = Quote(
            instrument_token=instrument_token,
            timestamp=timestamp,
            last_price=tick_data.get('last_price', 0),
            ohlc=ohlc,
            volume=tick_data.get('volume', 0),
            average_price=tick_data.get('average_price', 0),
            oi=tick_data.get('oi', 0)
        )
        
        self.quote_cache[instrument_token] = quote
        self.cache_timestamps[instrument_token] = timestamp
    
    def _process_tick_for_interval(self, instrument_token: int, timestamp: datetime,
                                  price: float, volume: int, 
                                  interval_name: str, interval_minutes: int) -> None:
        """Process tick for specific interval."""
        # Calculate candle timestamp (start of interval)
        candle_timestamp = self._get_candle_timestamp(timestamp, interval_minutes)
        
        # Get or create current candle
        current_candle = self.current_candles[interval_name][instrument_token]
        
        # Check if we need to start a new candle
        if (current_candle.tick_count == 0 or 
            current_candle.timestamp < candle_timestamp):
            
            # Save completed candle if exists
            if current_candle.tick_count > 0:
                self._complete_candle(instrument_token, interval_name, current_candle)
            
            # Start new candle
            current_candle = CandleData(timestamp=candle_timestamp, open=0, high=0, low=0, close=0)
            self.current_candles[interval_name][instrument_token] = current_candle
        
        # Update current candle with tick
        current_candle.update_tick(price, volume)
    
    def _get_candle_timestamp(self, timestamp: datetime, interval_minutes: int) -> datetime:
        """Get the start timestamp for a candle interval."""
        if interval_minutes >= 1440:  # Daily
            return timestamp.replace(hour=9, minute=15, second=0, microsecond=0)
        else:
            # Round down to interval start
            minutes = (timestamp.minute // interval_minutes) * interval_minutes
            return timestamp.replace(minute=minutes, second=0, microsecond=0)
    
    def _complete_candle(self, instrument_token: int, interval_name: str, 
                        candle: CandleData) -> None:
        """Complete and store a candle."""
        # Add to candles storage
        self.candles[interval_name][instrument_token].append(candle)
        
        # Trigger callbacks
        for callback in self.candle_callbacks[interval_name]:
            try:
                callback(instrument_token, interval_name, candle.to_ohlc())
            except Exception as e:
                print(f"Callback error: {e}")
    
    def get_latest_quote(self, instrument_token: int) -> Optional[Quote]:
        """Get latest quote for instrument."""
        with self._lock:
            quote = self.quote_cache.get(instrument_token)
            if not quote:
                return None
            
            # Check cache freshness
            cache_time = self.cache_timestamps.get(instrument_token)
            if cache_time and (datetime.now() - cache_time) > self.cache_ttl:
                return None
            
            return quote
    
    def get_candles(self, instrument_token: int, interval: str, 
                   count: int = 100) -> List[OHLC]:
        """Get historical candles for instrument."""
        with self._lock:
            if interval not in self.candles:
                return []
            
            candle_deque = self.candles[interval][instrument_token]
            if not candle_deque:
                return []
            
            # Get last 'count' candles
            start_idx = max(0, len(candle_deque) - count)
            return [candle.to_ohlc() for candle in list(candle_deque)[start_idx:]]
    
    def get_historical_data(self, instrument_token: int, interval: str, 
                          count: int = 100) -> HistoricalData:
        """Get historical data as pandas DataFrame."""
        candles = self.get_candles(instrument_token, interval, count)
        
        if not candles:
            return HistoricalData(
                instrument_token=instrument_token,
                interval=interval,
                data=pd.DataFrame()
            )
        
        # Convert to DataFrame
        data = []
        for i, candle in enumerate(candles):
            candle_data = self.candles[interval][instrument_token][-(count-i)]
            data.append({
                'date': candle_data.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume
            })
        
        df = pd.DataFrame(data)
        
        return HistoricalData(
            instrument_token=instrument_token,
            interval=interval,
            data=df
        )
    
    def add_candle_callback(self, interval: str, callback: Callable) -> None:
        """Add callback for candle completion."""
        self.candle_callbacks[interval].append(callback)
    
    def remove_candle_callback(self, interval: str, callback: Callable) -> None:
        """Remove callback for candle completion."""
        if callback in self.candle_callbacks[interval]:
            self.candle_callbacks[interval].remove(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        with self._lock:
            stats = {
                'instruments_tracked': len(self.latest_ticks),
                'cached_quotes': len(self.quote_cache),
                'intervals': {}
            }
            
            for interval in self.INTERVALS:
                interval_stats = {
                    'instruments': len(self.candles[interval]),
                    'total_candles': sum(len(candles) for candles in self.candles[interval].values()),
                    'current_building': len([c for c in self.current_candles[interval].values() if c.tick_count > 0])
                }
                stats['intervals'][interval] = interval_stats
            
            return stats
    
    def clear_data(self, instrument_token: int = None, interval: str = None) -> None:
        """Clear stored data."""
        with self._lock:
            if instrument_token and interval:
                # Clear specific instrument and interval
                self.candles[interval][instrument_token].clear()
                if instrument_token in self.current_candles[interval]:
                    del self.current_candles[interval][instrument_token]
            elif instrument_token:
                # Clear specific instrument from all intervals
                for interval_name in self.INTERVALS:
                    self.candles[interval_name][instrument_token].clear()
                    if instrument_token in self.current_candles[interval_name]:
                        del self.current_candles[interval_name][instrument_token]
                
                # Clear from caches
                self.latest_ticks.pop(instrument_token, None)
                self.quote_cache.pop(instrument_token, None)
                self.cache_timestamps.pop(instrument_token, None)
            elif interval:
                # Clear specific interval for all instruments
                self.candles[interval].clear()
                self.current_candles[interval].clear()
            else:
                # Clear everything
                for interval_name in self.INTERVALS:
                    self.candles[interval_name].clear()
                    self.current_candles[interval_name].clear()
                
                self.latest_ticks.clear()
                self.quote_cache.clear()
                self.cache_timestamps.clear()
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export all data to dictionary format."""
        with self._lock:
            export_data = {
                'latest_ticks': dict(self.latest_ticks),
                'candles': {},
                'quotes': {}
            }
            
            # Export candles
            for interval, instruments in self.candles.items():
                export_data['candles'][interval] = {}
                for token, candles in instruments.items():
                    export_data['candles'][interval][token] = [
                        {
                            'timestamp': candle.timestamp.isoformat(),
                            'open': candle.open,
                            'high': candle.high,
                            'low': candle.low,
                            'close': candle.close,
                            'volume': candle.volume
                        }
                        for candle in candles
                    ]
            
            # Export quotes
            for token, quote in self.quote_cache.items():
                export_data['quotes'][token] = quote.to_pandas_row()
            
            return export_data
