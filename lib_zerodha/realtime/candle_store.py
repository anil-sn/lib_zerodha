"""In-memory candle aggregation and persistent storage.
   Provides classes for real-time candle aggregation from tick data.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import pandas as pd
from pathlib import Path
import sqlite3
import json

from ..models.market_data import Quote, OHLC, HistoricalData
from ..exceptions.api_exceptions import StorageError


class InMemoryCandleStore:
    """Real-time candle aggregation from tick data.
    
    Aggregates incoming tick data into OHLCV candles for multiple timeframes
    with efficient memory management and thread-safe operations.
    """
    
    SUPPORTED_INTERVALS = {
        "1minute": 60,
        "2minute": 120, 
        "3minute": 180,
        "5minute": 300,
        "10minute": 600,
        "15minute": 900,
        "30minute": 1800,
        "60minute": 3600,
        "day": 86400
    }
    
    def __init__(self, max_candles_per_interval: int = 1000):
        """Initialize candle store.
        
        Args:
            max_candles_per_interval: Maximum candles to keep per interval
        """
        self.max_candles_per_interval = max_candles_per_interval
        
        # Structure: {instrument_token: {interval: [candles]}}
        self.candles: Dict[int, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        
        # Current incomplete candles: {instrument_token: {interval: candle_dict}}
        self.current_candles: Dict[int, Dict[str, Dict]] = defaultdict(dict)
        
        # Last tick timestamp for each instrument
        self.last_tick_time: Dict[int, datetime] = {}
        
        # Thread locks for thread safety
        self.locks: Dict[int, threading.Lock] = defaultdict(threading.Lock)
        
        # Statistics
        self.tick_count = 0
        self.candles_generated = 0
        
    def add_tick(self, quote: Any):
        """Add tick data and update candles."""
        instrument = quote.instrument_token
        tick_time = quote.timestamp
        
        if not isinstance(tick_time, datetime):
            tick_time = datetime.now()
        
        with self.locks[instrument]:
            self.tick_count += 1
            self.last_tick_time[instrument] = tick_time
            
            # Update candles for all intervals
            for interval_name, interval_seconds in self.SUPPORTED_INTERVALS.items():
                self._update_candle(instrument, quote, interval_name, interval_seconds, tick_time)
    
    def _update_candle(self, instrument: int, quote: Any, 
                      interval_name: str, interval_seconds: int, tick_time: datetime):
        """Update candle for specific interval."""
        # Calculate candle timestamp (start of period)
        candle_timestamp = self._get_candle_timestamp(tick_time, interval_seconds)
        
        # Get or create current candle
        if (interval_name not in self.current_candles[instrument] or
            self.current_candles[instrument][interval_name]['timestamp'] != candle_timestamp):
            
            # Save previous candle if it exists
            if interval_name in self.current_candles[instrument]:
                self._save_completed_candle(instrument, interval_name, 
                                          self.current_candles[instrument][interval_name])
            
            # Create new candle
            self.current_candles[instrument][interval_name] = {
                'timestamp': candle_timestamp,
                'open': quote.last_price,
                'high': quote.last_price,
                'low': quote.last_price,
                'close': quote.last_price,
                'volume': getattr(quote, 'volume', 0),
                'tick_count': 1
            }
        else:
            # Update existing candle
            candle = self.current_candles[instrument][interval_name]
            candle['high'] = max(candle['high'], quote.last_price)
            candle['low'] = min(candle['low'], quote.last_price)
            candle['close'] = quote.last_price
            candle['volume'] = getattr(quote, 'volume', 0)  # Use latest volume
            candle['tick_count'] += 1
    
    def _get_candle_timestamp(self, tick_time: datetime, interval_seconds: int) -> datetime:
        """Calculate candle start timestamp for given interval."""
        if interval_seconds >= 86400:  # Daily or higher
            return tick_time.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # For intraday intervals
            total_seconds = tick_time.hour * 3600 + tick_time.minute * 60 + tick_time.second
            candle_start_seconds = (total_seconds // interval_seconds) * interval_seconds
            
            hours = candle_start_seconds // 3600
            minutes = (candle_start_seconds % 3600) // 60
            seconds = candle_start_seconds % 60
            
            return tick_time.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
    
    def _save_completed_candle(self, instrument: int, interval_name: str, candle: Dict):
        """Save completed candle to history."""
        self.candles[instrument][interval_name].append(candle.copy())
        
        # Maintain max candles limit
        if len(self.candles[instrument][interval_name]) > self.max_candles_per_interval:
            self.candles[instrument][interval_name] = \
                self.candles[instrument][interval_name][-self.max_candles_per_interval:]
        
        self.candles_generated += 1
    
    def get_candles(self, instrument_token: int, interval: str, 
                   count: Optional[int] = None, include_incomplete: bool = False) -> List[Dict]:
        """Get candles for instrument and interval."""
        with self.locks[instrument_token]:
            candles = self.candles[instrument_token].get(interval, []).copy()
            
            if include_incomplete and interval in self.current_candles[instrument_token]:
                candles.append(self.current_candles[instrument_token][interval].copy())
                
            if count:
                return candles[-count:]
            return candles

    def clear(self):
        """Clear all candle data."""
        self.candles.clear()
        self.current_candles.clear()
        self.last_tick_time.clear()
        self.tick_count = 0
        self.candles_generated = 0
