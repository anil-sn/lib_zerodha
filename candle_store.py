"""In-memory candle aggregation and persistent storage.

Inspired by PKScreener's InMemoryCandleStore and LocalCandleDatabase
for real-time candle aggregation from tick data.
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

from .data_models import Quote, OHLC, HistoricalData
from .exceptions import StorageError


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
        
    def add_tick(self, quote: Quote):
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
    
    def _update_candle(self, instrument: int, quote: Quote, 
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
                'volume': quote.volume,
                'tick_count': 1
            }
        else:
            # Update existing candle
            candle = self.current_candles[instrument][interval_name]
            candle['high'] = max(candle['high'], quote.last_price)
            candle['low'] = min(candle['low'], quote.last_price)
            candle['close'] = quote.last_price
            candle['volume'] = quote.volume  # Use latest volume (cumulative)
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
        if instrument not in self.candles:
            self.candles[instrument] = defaultdict(list)
        
        self.candles[instrument][interval_name].append(candle.copy())
        
        # Maintain max candles limit
        if len(self.candles[instrument][interval_name]) > self.max_candles_per_interval:
            self.candles[instrument][interval_name] = \
                self.candles[instrument][interval_name][-self.max_candles_per_interval:]
        
        self.candles_generated += 1
    
    def get_candles(self, instrument_token: int, interval: str, 
                   count: Optional[int] = None, include_incomplete: bool = False) -> List[Dict]:
        """Get candles for instrument and interval.
        
        Args:
            instrument_token: Instrument token
            interval: Time interval (1minute, 5minute, etc.)
            count: Number of latest candles to return
            include_incomplete: Include current incomplete candle
            
        Returns:
            List of candle dictionaries
        """
        if instrument_token not in self.candles or interval not in self.candles[instrument_token]:
            return []
        
        with self.locks[instrument_token]:
            candles = self.candles[instrument_token][interval].copy()
            
            # Add incomplete candle if requested
            if (include_incomplete and 
                instrument_token in self.current_candles and
                interval in self.current_candles[instrument_token]):
                candles.append(self.current_candles[instrument_token][interval].copy())
            
            # Return latest N candles
            if count:
                candles = candles[-count:]
            
            return candles
    
    def get_historical_data(self, instrument_token: int, interval: str, 
                          count: int = 100) -> HistoricalData:
        """Get historical data as HistoricalData object."""
        candles = self.get_candles(instrument_token, interval, count)
        
        if not candles:
            # Return empty HistoricalData
            empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            return HistoricalData(instrument_token, empty_df)
        
        # Convert to DataFrame
        df_data = []
        for candle in candles:
            df_data.append({
                'timestamp': candle['timestamp'],
                'open': candle['open'],
                'high': candle['high'], 
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume']
            })
        
        df = pd.DataFrame(df_data)
        df.set_index('timestamp', inplace=True)
        
        return HistoricalData(instrument_token, df)
    
    def get_latest_price(self, instrument_token: int) -> Optional[float]:
        """Get latest price for instrument."""
        # Check current candle first
        for interval in ['1minute', '5minute']:  # Check short intervals
            if (instrument_token in self.current_candles and 
                interval in self.current_candles[instrument_token]):
                return self.current_candles[instrument_token][interval]['close']
        
        # Check completed candles
        for interval in ['1minute', '5minute']:
            if (instrument_token in self.candles and 
                interval in self.candles[instrument_token] and
                self.candles[instrument_token][interval]):
                return self.candles[instrument_token][interval][-1]['close']
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get candle store statistics."""
        total_instruments = len(self.candles)
        total_completed_candles = sum(
            sum(len(interval_candles) for interval_candles in instrument_candles.values())
            for instrument_candles in self.candles.values()
        )
        total_current_candles = sum(
            len(interval_candles)
            for interval_candles in self.current_candles.values()
        )
        
        return {
            'total_instruments': total_instruments,
            'total_completed_candles': total_completed_candles,
            'total_current_candles': total_current_candles,
            'total_ticks_processed': self.tick_count,
            'total_candles_generated': self.candles_generated,
            'supported_intervals': list(self.SUPPORTED_INTERVALS.keys()),
            'memory_usage_mb': self._estimate_memory_usage() / (1024 * 1024)
        }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes (rough calculation)."""
        # Rough estimate: each candle ~200 bytes
        completed_candles = sum(
            sum(len(interval_candles) for interval_candles in instrument_candles.values())
            for instrument_candles in self.candles.values()
        )
        current_candles = sum(
            len(interval_candles)
            for interval_candles in self.current_candles.values()
        )
        
        return (completed_candles + current_candles) * 200
    
    def clear_data(self, instrument_token: Optional[int] = None, older_than: Optional[datetime] = None):
        """Clear candle data.
        
        Args:
            instrument_token: Clear data for specific instrument (None for all)
            older_than: Clear data older than this timestamp
        """
        if instrument_token is not None:
            # Clear specific instrument
            if older_than:
                # Clear old data only
                with self.locks[instrument_token]:
                    for interval in self.candles[instrument_token]:
                        self.candles[instrument_token][interval] = [
                            candle for candle in self.candles[instrument_token][interval]
                            if candle['timestamp'] >= older_than
                        ]
            else:
                # Clear all data for instrument
                with self.locks[instrument_token]:
                    if instrument_token in self.candles:
                        del self.candles[instrument_token]
                    if instrument_token in self.current_candles:
                        del self.current_candles[instrument_token]
        else:
            # Clear all data
            if older_than:
                for instrument in list(self.candles.keys()):
                    self.clear_data(instrument, older_than)
            else:
                self.candles.clear()
                self.current_candles.clear()


class LocalCandleDatabase:
    """Persistent storage for candle data.
    
    Provides SQLite-based storage for candle data with efficient querying
    and data management capabilities.
    """
    
    def __init__(self, db_path: str = "candles.db"):
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    instrument_token INTEGER,
                    interval TEXT,
                    timestamp DATETIME,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    tick_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (instrument_token, interval, timestamp)
                )
            """)
            
            # Create indexes for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candles_instrument_interval 
                ON candles(instrument_token, interval)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candles_timestamp 
                ON candles(timestamp)
            """)
            
            # Metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_candles(self, instrument_token: int, interval: str, candles: List[Dict]):
        """Save candles to database.
        
        Args:
            instrument_token: Instrument token
            interval: Time interval 
            candles: List of candle dictionaries
        """
        if not candles:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for candle in candles:
                    conn.execute("""
                        INSERT OR REPLACE INTO candles 
                        (instrument_token, interval, timestamp, open, high, low, close, volume, tick_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        instrument_token,
                        interval,
                        candle['timestamp'],
                        candle['open'],
                        candle['high'],
                        candle['low'], 
                        candle['close'],
                        candle['volume'],
                        candle.get('tick_count', 0)
                    ))
                conn.commit()
                
        except Exception as e:
            raise StorageError(f"Failed to save candles: {e}")
    
    def load_candles(self, instrument_token: int, interval: str,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    count: Optional[int] = None) -> List[Dict]:
        """Load candles from database.
        
        Args:
            instrument_token: Instrument token
            interval: Time interval
            start_time: Start timestamp filter
            end_time: End timestamp filter
            count: Maximum number of candles to return (latest)
            
        Returns:
            List of candle dictionaries
        """
        query = """
            SELECT timestamp, open, high, low, close, volume, tick_count
            FROM candles 
            WHERE instrument_token = ? AND interval = ?
        """
        params = [instrument_token, interval]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp"
        
        if count:
            query += f" DESC LIMIT {count}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                candles = []
                for row in cursor.fetchall():
                    candles.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume'],
                        'tick_count': row['tick_count']
                    })
                
                # If we used DESC LIMIT, reverse to get chronological order
                if count:
                    candles.reverse()
                
                return candles
                
        except Exception as e:
            raise StorageError(f"Failed to load candles: {e}")
    
    def get_historical_data(self, instrument_token: int, interval: str,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          count: Optional[int] = None) -> HistoricalData:
        """Get historical data as HistoricalData object."""
        candles = self.load_candles(instrument_token, interval, start_time, end_time, count)
        
        if not candles:
            # Return empty HistoricalData
            empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            return HistoricalData(instrument_token, empty_df)
        
        # Convert to DataFrame
        df_data = []
        for candle in candles:
            df_data.append({
                'timestamp': candle['timestamp'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume']
            })
        
        df = pd.DataFrame(df_data)
        df.set_index('timestamp', inplace=True)
        
        return HistoricalData(instrument_token, df)
    
    def cleanup_old_data(self, older_than: datetime):
        """Remove old candle data.
        
        Args:
            older_than: Remove data older than this timestamp
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM candles WHERE timestamp < ?",
                    [older_than]
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                return deleted_count
                
        except Exception as e:
            raise StorageError(f"Failed to cleanup old data: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total candles
                total_candles = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
                
                # Unique instruments
                unique_instruments = conn.execute(
                    "SELECT COUNT(DISTINCT instrument_token) FROM candles"
                ).fetchone()[0]
                
                # Date range
                date_range = conn.execute(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM candles"
                ).fetchone()
                
                # Intervals
                intervals = conn.execute(
                    "SELECT DISTINCT interval FROM candles"
                ).fetchall()
                
                # Database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'total_candles': total_candles,
                    'unique_instruments': unique_instruments,
                    'earliest_data': date_range[0],
                    'latest_data': date_range[1],
                    'available_intervals': [row[0] for row in intervals],
                    'database_size_mb': db_size / (1024 * 1024)
                }
                
        except Exception as e:
            raise StorageError(f"Failed to get database stats: {e}")