"""Real-time data handlers for processing market ticks."""

from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
from collections import deque, defaultdict
import threading

from ..models.market_data import Tick, Quote, OHLC
from ..storage.base_storage import TickStorage
from ..exceptions.api_exceptions import DataNotAvailableError


class TickAggregator:
    """Aggregates real-time ticks into OHLCV candles."""
    
    def __init__(self, interval_seconds: int = 60):
        """Initialize tick aggregator.
        
        Args:
            interval_seconds: Candle interval in seconds
        """
        self.interval_seconds = interval_seconds
        self._candles = {}  # instrument_token -> current candle
        self._completed_candles = defaultdict(deque)  # instrument_token -> candle history
        self._max_history = 1000  # Keep last 1000 candles per instrument
        self._lock = threading.RLock()
        
        # Callbacks
        self._on_candle_callbacks = []
    
    def process_tick(self, tick: Tick):
        """Process incoming tick and update candles.
        
        Args:
            tick: Market tick
        """
        with self._lock:
            instrument_token = tick.instrument_token
            current_time = tick.timestamp
            
            # Calculate candle start time
            candle_start = self._get_candle_start_time(current_time)
            
            # Get or create current candle
            if instrument_token not in self._candles:
                self._candles[instrument_token] = self._create_new_candle(
                    instrument_token, candle_start, tick
                )
            else:
                current_candle = self._candles[instrument_token]
                
                # Check if we need a new candle
                if candle_start > current_candle['timestamp']:
                    # Complete current candle
                    self._complete_candle(instrument_token, current_candle)
                    
                    # Start new candle
                    self._candles[instrument_token] = self._create_new_candle(
                        instrument_token, candle_start, tick
                    )
                else:
                    # Update current candle
                    self._update_candle(current_candle, tick)
    
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """Get candle start time for given timestamp."""
        total_seconds = int(timestamp.timestamp())
        candle_seconds = (total_seconds // self.interval_seconds) * self.interval_seconds
        return datetime.fromtimestamp(candle_seconds)
    
    def _create_new_candle(self, instrument_token: int, 
                          start_time: datetime, tick: Tick) -> Dict[str, Any]:
        """Create new candle from tick."""
        return {
            'instrument_token': instrument_token,
            'timestamp': start_time,
            'open': tick.last_price,
            'high': tick.last_price,
            'low': tick.last_price,
            'close': tick.last_price,
            'volume': tick.volume or 0,
            'oi': tick.oi or 0,
            'tick_count': 1
        }
    
    def _update_candle(self, candle: Dict[str, Any], tick: Tick):
        """Update existing candle with new tick."""
        candle['high'] = max(candle['high'], tick.last_price)
        candle['low'] = min(candle['low'], tick.last_price)
        candle['close'] = tick.last_price
        
        if tick.volume:
            candle['volume'] = tick.volume
        if tick.oi is not None:
            candle['oi'] = tick.oi
            
        candle['tick_count'] += 1
    
    def _complete_candle(self, instrument_token: int, candle: Dict[str, Any]):
        """Complete candle and notify callbacks."""
        # Add to history
        history = self._completed_candles[instrument_token]
        history.append(candle.copy())
        
        # Limit history size
        if len(history) > self._max_history:
            history.popleft()
        
        # Notify callbacks
        for callback in self._on_candle_callbacks:
            try:
                callback(candle.copy())
            except Exception:
                pass  # Don't let callback errors break processing
    
    def get_current_candle(self, instrument_token: int) -> Optional[Dict[str, Any]]:
        """Get current incomplete candle."""
        with self._lock:
            return self._candles.get(instrument_token, {}).copy()
    
    def get_candle_history(self, instrument_token: int, 
                          count: int = 100) -> List[Dict[str, Any]]:
        """Get completed candle history."""
        with self._lock:
            history = self._completed_candles[instrument_token]
            return list(history)[-count:] if history else []
    
    def on_candle_complete(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for completed candles."""
        self._on_candle_callbacks.append(callback)


class MarketDepthProcessor:
    """Processes market depth data from ticks."""
    
    def __init__(self):
        """Initialize market depth processor."""
        self._depth_data = {}  # instrument_token -> depth data
        self._lock = threading.RLock()
        
        # Callbacks
        self._on_depth_callbacks = []
    
    def process_tick(self, tick: Tick):
        """Process tick for market depth updates.
        
        Args:
            tick: Market tick with depth data
        """
        if not hasattr(tick, 'depth') or not tick.depth:
            return
        
        with self._lock:
            instrument_token = tick.instrument_token
            
            # Update depth data
            self._depth_data[instrument_token] = {
                'instrument_token': instrument_token,
                'timestamp': tick.timestamp,
                'buy': tick.depth.get('buy', []),
                'sell': tick.depth.get('sell', []),
                'last_price': tick.last_price,
                'volume': tick.volume
            }
            
            # Notify callbacks
            for callback in self._on_depth_callbacks:
                try:
                    callback(self._depth_data[instrument_token].copy())
                except Exception:
                    pass
    
    def get_market_depth(self, instrument_token: int) -> Optional[Dict[str, Any]]:
        """Get current market depth."""
        with self._lock:
            return self._depth_data.get(instrument_token, {}).copy()
    
    def on_depth_update(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for depth updates."""
        self._on_depth_callbacks.append(callback)


class TickBuffer:
    """Buffers ticks and provides batch processing."""
    
    def __init__(self, buffer_size: int = 1000, 
                 flush_interval: float = 1.0,
                 storage: Optional[TickStorage] = None):
        """Initialize tick buffer.
        
        Args:
            buffer_size: Maximum ticks to buffer
            flush_interval: Flush interval in seconds
            storage: Storage for persisting ticks
        """
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.storage = storage
        
        self._buffer = deque()
        self._lock = threading.RLock()
        self._last_flush = datetime.now()
        
        # Start background flush thread
        self._flush_thread = threading.Thread(
            target=self._background_flush,
            daemon=True
        )
        self._flush_thread.start()
    
    def add_tick(self, tick: Tick):
        """Add tick to buffer."""
        with self._lock:
            self._buffer.append(tick)
            
            # Check if buffer needs flushing
            if (len(self._buffer) >= self.buffer_size or 
                (datetime.now() - self._last_flush).total_seconds() >= self.flush_interval):
                self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush buffer to storage."""
        if not self._buffer:
            return
        
        ticks_to_flush = list(self._buffer)
        self._buffer.clear()
        self._last_flush = datetime.now()
        
        # Persist to storage if available
        if self.storage:
            try:
                self.storage.save_ticks(ticks_to_flush)
            except Exception:
                pass  # Don't let storage errors break tick processing
    
    def _background_flush(self):
        """Background thread for periodic flushing."""
        while True:
            try:
                with self._lock:
                    if ((datetime.now() - self._last_flush).total_seconds() 
                        >= self.flush_interval and self._buffer):
                        self._flush_buffer()
            except Exception:
                pass
            
            # Sleep for a fraction of flush interval
            threading.Event().wait(self.flush_interval / 10)
    
    def flush(self):
        """Manually flush buffer."""
        with self._lock:
            self._flush_buffer()
    
    def get_buffer_size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)


class RealTimeQuoteManager:
    """Manages real-time quotes and provides latest data."""
    
    def __init__(self, max_age_seconds: float = 10.0):
        """Initialize quote manager.
        
        Args:
            max_age_seconds: Maximum age for quotes to be considered fresh
        """
        self.max_age_seconds = max_age_seconds
        self._quotes = {}  # instrument_token -> Quote
        self._lock = threading.RLock()
        
        # Callbacks
        self._on_quote_callbacks = []
    
    def process_tick(self, tick: Tick):
        """Process tick and update quote."""
        with self._lock:
            instrument_token = tick.instrument_token
            
            # Create or update quote
            quote = Quote(
                instrument_token=instrument_token,
                timestamp=tick.timestamp,
                last_price=tick.last_price,
                volume=tick.volume or 0,
                average_price=tick.average_price or 0.0,
                ohlc=tick.ohlc if tick.ohlc else OHLC(0,0,0,0),
                depth=tick.depth if tick.depth else {"buy": [], "sell": []},
                oi=tick.oi or 0
            )
            
            self._quotes[instrument_token] = quote
            
            # Notify callbacks
            for callback in self._on_quote_callbacks:
                try:
                    callback(quote)
                except Exception:
                    pass
    
    def get_quote(self, instrument_token: int) -> Optional[Quote]:
        """Get latest quote for instrument."""
        with self._lock:
            quote = self._quotes.get(instrument_token)
            
            if quote:
                # Check if quote is fresh
                age = (datetime.now() - quote.timestamp).total_seconds()
                if age <= self.max_age_seconds:
                    return quote
            
            return None
    
    def get_quotes(self, instrument_tokens: List[int]) -> Dict[int, Quote]:
        """Get quotes for multiple instruments."""
        quotes = {}
        for token in instrument_tokens:
            quote = self.get_quote(token)
            if quote:
                quotes[token] = quote
        return quotes
    
    def get_all_quotes(self) -> Dict[int, Quote]:
        """Get all fresh quotes."""
        quotes = {}
        current_time = datetime.now()
        
        with self._lock:
            for token, quote in self._quotes.items():
                age = (current_time - quote.timestamp).total_seconds()
                if age <= self.max_age_seconds:
                    quotes[token] = quote
        
        return quotes
    
    def cleanup_old_quotes(self):
        """Remove old quotes from memory."""
        current_time = datetime.now()
        
        with self._lock:
            to_remove = []
            for token, quote in self._quotes.items():
                age = (current_time - quote.timestamp).total_seconds()
                if age > self.max_age_seconds * 2:  # Double the age for cleanup
                    to_remove.append(token)
            
            for token in to_remove:
                del self._quotes[token]
    
    def on_quote_update(self, callback: Callable[[Quote], None]):
        """Register callback for quote updates."""
        self._on_quote_callbacks.append(callback)