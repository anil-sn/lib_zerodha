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
            candle['tick_count'] += 1\n    \n    def _get_candle_timestamp(self, tick_time: datetime, interval_seconds: int) -> datetime:\n        \"\"\"Calculate candle start timestamp for given interval.\"\"\"\n        if interval_seconds >= 86400:  # Daily or higher\n            return tick_time.replace(hour=0, minute=0, second=0, microsecond=0)\n        else:\n            # For intraday intervals\n            total_seconds = tick_time.hour * 3600 + tick_time.minute * 60 + tick_time.second\n            candle_start_seconds = (total_seconds // interval_seconds) * interval_seconds\n            \n            hours = candle_start_seconds // 3600\n            minutes = (candle_start_seconds % 3600) // 60\n            seconds = candle_start_seconds % 60\n            \n            return tick_time.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)\n    \n    def _save_completed_candle(self, instrument: int, interval_name: str, candle: Dict):\n        \"\"\"Save completed candle to history.\"\"\"\n        if instrument not in self.candles:\n            self.candles[instrument] = defaultdict(list)\n        \n        self.candles[instrument][interval_name].append(candle.copy())\n        \n        # Maintain max candles limit\n        if len(self.candles[instrument][interval_name]) > self.max_candles_per_interval:\n            self.candles[instrument][interval_name] = \\\n                self.candles[instrument][interval_name][-self.max_candles_per_interval:]\n        \n        self.candles_generated += 1\n    \n    def get_candles(self, instrument_token: int, interval: str, \n                   count: Optional[int] = None, include_incomplete: bool = False) -> List[Dict]:\n        \"\"\"Get candles for instrument and interval.\n        \n        Args:\n            instrument_token: Instrument token\n            interval: Time interval (1minute, 5minute, etc.)\n            count: Number of latest candles to return\n            include_incomplete: Include current incomplete candle\n            \n        Returns:\n            List of candle dictionaries\n        \"\"\"\n        if instrument_token not in self.candles or interval not in self.candles[instrument_token]:\n            return []\n        \n        with self.locks[instrument_token]:\n            candles = self.candles[instrument_token][interval].copy()\n            \n            # Add incomplete candle if requested\n            if (include_incomplete and \n                instrument_token in self.current_candles and\n                interval in self.current_candles[instrument_token]):\n                candles.append(self.current_candles[instrument_token][interval].copy())\n            \n            # Return latest N candles\n            if count:\n                candles = candles[-count:]\n            \n            return candles\n    \n    def get_historical_data(self, instrument_token: int, interval: str, \n                          count: int = 100) -> HistoricalData:\n        \"\"\"Get historical data as HistoricalData object.\"\"\"\n        candles = self.get_candles(instrument_token, interval, count)\n        \n        if not candles:\n            # Return empty HistoricalData\n            empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])\n            return HistoricalData(instrument_token, empty_df)\n        \n        # Convert to DataFrame\n        df_data = []\n        for candle in candles:\n            df_data.append({\n                'timestamp': candle['timestamp'],\n                'open': candle['open'],\n                'high': candle['high'], \n                'low': candle['low'],\n                'close': candle['close'],\n                'volume': candle['volume']\n            })\n        \n        df = pd.DataFrame(df_data)\n        df.set_index('timestamp', inplace=True)\n        \n        return HistoricalData(instrument_token, df)\n    \n    def get_latest_price(self, instrument_token: int) -> Optional[float]:\n        \"\"\"Get latest price for instrument.\"\"\"\n        # Check current candle first\n        for interval in ['1minute', '5minute']:  # Check short intervals\n            if (instrument_token in self.current_candles and \n                interval in self.current_candles[instrument_token]):\n                return self.current_candles[instrument_token][interval]['close']\n        \n        # Check completed candles\n        for interval in ['1minute', '5minute']:\n            if (instrument_token in self.candles and \n                interval in self.candles[instrument_token] and\n                self.candles[instrument_token][interval]):\n                return self.candles[instrument_token][interval][-1]['close']\n        \n        return None\n    \n    def get_statistics(self) -> Dict[str, Any]:\n        \"\"\"Get candle store statistics.\"\"\"\n        total_instruments = len(self.candles)\n        total_completed_candles = sum(\n            sum(len(interval_candles) for interval_candles in instrument_candles.values())\n            for instrument_candles in self.candles.values()\n        )\n        total_current_candles = sum(\n            len(interval_candles)\n            for interval_candles in self.current_candles.values()\n        )\n        \n        return {\n            'total_instruments': total_instruments,\n            'total_completed_candles': total_completed_candles,\n            'total_current_candles': total_current_candles,\n            'total_ticks_processed': self.tick_count,\n            'total_candles_generated': self.candles_generated,\n            'supported_intervals': list(self.SUPPORTED_INTERVALS.keys()),\n            'memory_usage_mb': self._estimate_memory_usage() / (1024 * 1024)\n        }\n    \n    def _estimate_memory_usage(self) -> int:\n        \"\"\"Estimate memory usage in bytes (rough calculation).\"\"\"\n        # Rough estimate: each candle ~200 bytes\n        completed_candles = sum(\n            sum(len(interval_candles) for interval_candles in instrument_candles.values())\n            for instrument_candles in self.candles.values()\n        )\n        current_candles = sum(\n            len(interval_candles)\n            for interval_candles in self.current_candles.values()\n        )\n        \n        return (completed_candles + current_candles) * 200\n    \n    def clear_data(self, instrument_token: Optional[int] = None, older_than: Optional[datetime] = None):\n        \"\"\"Clear candle data.\n        \n        Args:\n            instrument_token: Clear data for specific instrument (None for all)\n            older_than: Clear data older than this timestamp\n        \"\"\"\n        if instrument_token is not None:\n            # Clear specific instrument\n            if older_than:\n                # Clear old data only\n                with self.locks[instrument_token]:\n                    for interval in self.candles[instrument_token]:\n                        self.candles[instrument_token][interval] = [\n                            candle for candle in self.candles[instrument_token][interval]\n                            if candle['timestamp'] >= older_than\n                        ]\n            else:\n                # Clear all data for instrument\n                with self.locks[instrument_token]:\n                    if instrument_token in self.candles:\n                        del self.candles[instrument_token]\n                    if instrument_token in self.current_candles:\n                        del self.current_candles[instrument_token]\n        else:\n            # Clear all data\n            if older_than:\n                for instrument in list(self.candles.keys()):\n                    self.clear_data(instrument, older_than)\n            else:\n                self.candles.clear()\n                self.current_candles.clear()\n\n\nclass LocalCandleDatabase:\n    \"\"\"Persistent storage for candle data.\n    \n    Provides SQLite-based storage for candle data with efficient querying\n    and data management capabilities.\n    \"\"\"\n    \n    def __init__(self, db_path: str = \"candles.db\"):\n        \"\"\"Initialize database.\n        \n        Args:\n            db_path: Path to SQLite database file\n        \"\"\"\n        self.db_path = Path(db_path)\n        self.db_path.parent.mkdir(parents=True, exist_ok=True)\n        \n        self._init_database()\n    \n    def _init_database(self):\n        \"\"\"Initialize database schema.\"\"\"\n        with sqlite3.connect(self.db_path) as conn:\n            conn.execute(\"\"\"\n                CREATE TABLE IF NOT EXISTS candles (\n                    instrument_token INTEGER,\n                    interval TEXT,\n                    timestamp DATETIME,\n                    open REAL,\n                    high REAL,\n                    low REAL,\n                    close REAL,\n                    volume INTEGER,\n                    tick_count INTEGER DEFAULT 0,\n                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,\n                    PRIMARY KEY (instrument_token, interval, timestamp)\n                )\n            \"\"\")\n            \n            # Create indexes for better performance\n            conn.execute(\"\"\"\n                CREATE INDEX IF NOT EXISTS idx_candles_instrument_interval \n                ON candles(instrument_token, interval)\n            \"\"\")\n            \n            conn.execute(\"\"\"\n                CREATE INDEX IF NOT EXISTS idx_candles_timestamp \n                ON candles(timestamp)\n            \"\"\")\n            \n            # Metadata table\n            conn.execute(\"\"\"\n                CREATE TABLE IF NOT EXISTS metadata (\n                    key TEXT PRIMARY KEY,\n                    value TEXT,\n                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP\n                )\n            \"\"\")\n            \n            conn.commit()\n    \n    def save_candles(self, instrument_token: int, interval: str, candles: List[Dict]):\n        \"\"\"Save candles to database.\n        \n        Args:\n            instrument_token: Instrument token\n            interval: Time interval \n            candles: List of candle dictionaries\n        \"\"\"\n        if not candles:\n            return\n        \n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                for candle in candles:\n                    conn.execute(\"\"\"\n                        INSERT OR REPLACE INTO candles \n                        (instrument_token, interval, timestamp, open, high, low, close, volume, tick_count)\n                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\n                    \"\"\", (\n                        instrument_token,\n                        interval,\n                        candle['timestamp'],\n                        candle['open'],\n                        candle['high'],\n                        candle['low'], \n                        candle['close'],\n                        candle['volume'],\n                        candle.get('tick_count', 0)\n                    ))\n                conn.commit()\n                \n        except Exception as e:\n            raise StorageError(f\"Failed to save candles: {e}\")\n    \n    def load_candles(self, instrument_token: int, interval: str,\n                    start_time: Optional[datetime] = None,\n                    end_time: Optional[datetime] = None,\n                    count: Optional[int] = None) -> List[Dict]:\n        \"\"\"Load candles from database.\n        \n        Args:\n            instrument_token: Instrument token\n            interval: Time interval\n            start_time: Start timestamp filter\n            end_time: End timestamp filter\n            count: Maximum number of candles to return (latest)\n            \n        Returns:\n            List of candle dictionaries\n        \"\"\"\n        query = \"\"\"\n            SELECT timestamp, open, high, low, close, volume, tick_count\n            FROM candles \n            WHERE instrument_token = ? AND interval = ?\n        \"\"\"\n        params = [instrument_token, interval]\n        \n        if start_time:\n            query += \" AND timestamp >= ?\"\n            params.append(start_time)\n        \n        if end_time:\n            query += \" AND timestamp <= ?\"\n            params.append(end_time)\n        \n        query += \" ORDER BY timestamp\"\n        \n        if count:\n            query += f\" DESC LIMIT {count}\"\n        \n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                conn.row_factory = sqlite3.Row\n                cursor = conn.execute(query, params)\n                \n                candles = []\n                for row in cursor.fetchall():\n                    candles.append({\n                        'timestamp': datetime.fromisoformat(row['timestamp']),\n                        'open': row['open'],\n                        'high': row['high'],\n                        'low': row['low'],\n                        'close': row['close'],\n                        'volume': row['volume'],\n                        'tick_count': row['tick_count']\n                    })\n                \n                # If we used DESC LIMIT, reverse to get chronological order\n                if count:\n                    candles.reverse()\n                \n                return candles\n                \n        except Exception as e:\n            raise StorageError(f\"Failed to load candles: {e}\")\n    \n    def get_historical_data(self, instrument_token: int, interval: str,\n                          start_time: Optional[datetime] = None,\n                          end_time: Optional[datetime] = None,\n                          count: Optional[int] = None) -> HistoricalData:\n        \"\"\"Get historical data as HistoricalData object.\"\"\"\n        candles = self.load_candles(instrument_token, interval, start_time, end_time, count)\n        \n        if not candles:\n            # Return empty HistoricalData\n            empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])\n            return HistoricalData(instrument_token, empty_df)\n        \n        # Convert to DataFrame\n        df_data = []\n        for candle in candles:\n            df_data.append({\n                'timestamp': candle['timestamp'],\n                'open': candle['open'],\n                'high': candle['high'],\n                'low': candle['low'],\n                'close': candle['close'],\n                'volume': candle['volume']\n            })\n        \n        df = pd.DataFrame(df_data)\n        df.set_index('timestamp', inplace=True)\n        \n        return HistoricalData(instrument_token, df)\n    \n    def cleanup_old_data(self, older_than: datetime):\n        \"\"\"Remove old candle data.\n        \n        Args:\n            older_than: Remove data older than this timestamp\n        \"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                cursor = conn.execute(\n                    \"DELETE FROM candles WHERE timestamp < ?\",\n                    [older_than]\n                )\n                deleted_count = cursor.rowcount\n                conn.commit()\n                \n                return deleted_count\n                \n        except Exception as e:\n            raise StorageError(f\"Failed to cleanup old data: {e}\")\n    \n    def get_database_stats(self) -> Dict[str, Any]:\n        \"\"\"Get database statistics.\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                # Total candles\n                total_candles = conn.execute(\"SELECT COUNT(*) FROM candles\").fetchone()[0]\n                \n                # Unique instruments\n                unique_instruments = conn.execute(\n                    \"SELECT COUNT(DISTINCT instrument_token) FROM candles\"\n                ).fetchone()[0]\n                \n                # Date range\n                date_range = conn.execute(\n                    \"SELECT MIN(timestamp), MAX(timestamp) FROM candles\"\n                ).fetchone()\n                \n                # Intervals\n                intervals = conn.execute(\n                    \"SELECT DISTINCT interval FROM candles\"\n                ).fetchall()\n                \n                # Database size\n                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0\n                \n                return {\n                    'total_candles': total_candles,\n                    'unique_instruments': unique_instruments,\n                    'earliest_data': date_range[0],\n                    'latest_data': date_range[1],\n                    'available_intervals': [row[0] for row in intervals],\n                    'database_size_mb': db_size / (1024 * 1024)\n                }\n                \n        except Exception as e:\n            raise StorageError(f\"Failed to get database stats: {e}\")