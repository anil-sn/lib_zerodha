"""Memory storage implementation for lib_zerodha."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, DefaultDict
from collections import defaultdict
import pandas as pd

from ..storage.base_storage import (
    CandleStorage, TickStorage, InstrumentStorage, 
    PortfolioStorage, BaseStorage
)
from ..models.market_data import HistoricalData, Tick
from ..models.portfolio import Position, Holding


class MemoryStorage(BaseStorage):
    """In-memory storage implementation."""
    
    def __init__(self):
        """Initialize memory storage."""
        self._data = {
            'candles': defaultdict(list),  # instrument_token -> List[HistoricalData]
            'ticks': defaultdict(list),    # instrument_token -> List[Tick]
            'instruments': pd.DataFrame(), # Instruments DataFrame
            'positions': [],               # List[Position]
            'holdings': [],                # List[Holding]
            'sessions': {}                 # session data
        }
    
    def close(self) -> None:
        """Close storage (no-op for memory)."""
        pass
    
    def clear(self) -> None:
        """Clear all data."""
        self._data['candles'].clear()
        self._data['ticks'].clear()
        self._data['instruments'] = pd.DataFrame()
        self._data['positions'].clear()
        self._data['holdings'].clear()
        self._data['sessions'].clear()


class MemoryCandleStorage(CandleStorage, MemoryStorage):
    """In-memory storage for candle data."""
    
    def connect(self) -> bool:
        """Establish connection (no-op for memory storage)."""
        return True
    
    def disconnect(self) -> bool:
        """Close connection (no-op for memory storage)."""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return {
            'status': 'healthy',
            'type': 'memory',
            'candle_count': sum(len(candles) for candles in self._data['candles'].values())
        }
    
    def store_candle(self, instrument_token: int, interval: str, candle: HistoricalData) -> bool:
        """Store single candle."""
        try:
            self.save_candles([candle])
            return True
        except Exception:
            return False
    
    def store_candles_batch(self, candles: List[HistoricalData], interval: str) -> int:
        """Store multiple candles."""
        try:
            self.save_candles(candles)
            return len(candles)
        except Exception:
            return 0
    
    def get_latest_candle(self, instrument_token: int, interval: str) -> Optional[HistoricalData]:
        """Get most recent candle for instrument."""
        candles = self._data['candles'][instrument_token]
        return candles[-1] if candles else None
    
    def delete_old_candles(self, older_than: datetime, interval: Optional[str] = None) -> int:
        """Delete candles older than specified time."""
        deleted_count = 0
        for token in self._data['candles']:
            original_count = len(self._data['candles'][token])
            self._data['candles'][token] = [
                candle for candle in self._data['candles'][token]
                if candle.timestamp >= older_than
            ]
            deleted_count += original_count - len(self._data['candles'][token])
        return deleted_count
    
    def save_candles(self, candles: List[HistoricalData]) -> None:
        """Save candle data to memory."""
        for candle in candles:
            token = candle.instrument_token
            
            # Remove existing candle with same timestamp
            self._data['candles'][token] = [
                c for c in self._data['candles'][token]
                if c.timestamp != candle.timestamp
            ]
            
            # Add new candle
            self._data['candles'][token].append(candle)
            
            # Keep sorted by timestamp
            self._data['candles'][token].sort(key=lambda x: x.timestamp)
    
    def get_candles(self, instrument_token: int, from_date: date, 
                   to_date: date) -> List[HistoricalData]:
        """Get candle data from memory."""
        candles = self._data['candles'][instrument_token]
        
        # Convert dates to datetime for comparison
        from_datetime = datetime.combine(from_date, datetime.min.time())
        to_datetime = datetime.combine(to_date, datetime.max.time())
        
        # Filter by date range
        filtered = [
            candle for candle in candles
            if from_datetime <= candle.timestamp <= to_datetime
        ]
        
        return sorted(filtered, key=lambda x: x.timestamp)
    
    def delete_candles(self, instrument_token: int, before_date: date) -> None:
        """Delete old candle data."""
        before_datetime = datetime.combine(before_date, datetime.max.time())
        
        self._data['candles'][instrument_token] = [
            candle for candle in self._data['candles'][instrument_token]
            if candle.timestamp >= before_datetime
        ]


class MemoryTickStorage(TickStorage, MemoryStorage):
    """In-memory storage for tick data."""
    
    def connect(self) -> bool:
        """Establish connection (no-op for memory storage)."""
        return True
    
    def disconnect(self) -> bool:
        """Close connection (no-op for memory storage)."""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return {
            'status': 'healthy',
            'type': 'memory',
            'tick_count': sum(len(ticks) for ticks in self._data['ticks'].values())
        }
    
    def store_tick(self, tick: Tick) -> bool:
        """Store single tick."""
        try:
            self.save_ticks([tick])
            return True
        except Exception:
            return False
    
    def store_ticks_batch(self, ticks: List[Tick]) -> int:
        """Store multiple ticks."""
        try:
            self.save_ticks(ticks)
            return len(ticks)
        except Exception:
            return 0
    
    def get_latest_tick(self, instrument_token: int) -> Optional[Tick]:
        """Get most recent tick for instrument."""
        ticks = self._data['ticks'][instrument_token]
        return ticks[-1] if ticks else None
    
    def save_ticks(self, ticks: List[Tick]) -> None:
        """Save tick data to memory."""
        for tick in ticks:
            token = tick.instrument_token
            
            # Remove existing tick with same timestamp
            self._data['ticks'][token] = [
                t for t in self._data['ticks'][token]
                if t.timestamp != tick.timestamp
            ]
            
            # Add new tick
            self._data['ticks'][token].append(tick)
            
            # Keep sorted by timestamp
            self._data['ticks'][token].sort(key=lambda x: x.timestamp)
    
    def get_ticks(self, instrument_token: int, from_time: datetime, 
                 to_time: datetime) -> List[Tick]:
        """Get tick data from memory."""
        ticks = self._data['ticks'][instrument_token]
        
        # Filter by time range
        filtered = [
            tick for tick in ticks
            if from_time <= tick.timestamp <= to_time
        ]
        
        return sorted(filtered, key=lambda x: x.timestamp)
    
    def delete_ticks(self, instrument_token: int, before_time: datetime) -> None:
        """Delete old tick data."""
        self._data['ticks'][instrument_token] = [
            tick for tick in self._data['ticks'][instrument_token]
            if tick.timestamp >= before_time
        ]


class MemoryInstrumentStorage(InstrumentStorage, MemoryStorage):
    """In-memory storage for instrument data."""
    
    def connect(self) -> bool:
        """Establish connection (no-op for memory storage)."""
        return True
    
    def disconnect(self) -> bool:
        """Close connection (no-op for memory storage)."""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return {
            'status': 'healthy',
            'type': 'memory',
            'instrument_count': len(self._data['instruments'])
        }
    
    def store_instruments(self, instruments: List[Any]) -> int:
        """Store instrument metadata."""
        # Convert to DataFrame if not already
        if isinstance(instruments, list) and len(instruments) > 0:
            # Assuming instruments are dict-like
            df = pd.DataFrame(instruments)
            self._data['instruments'] = df
            return len(instruments)
        return 0
    
    def get_instrument(self, instrument_token: int) -> Optional[Dict[str, Any]]:
        """Get instrument by token."""
        return self.get_instrument_by_token(instrument_token)
    
    def save_instruments(self, instruments: pd.DataFrame) -> None:
        """Save instrument data to memory."""
        self._data['instruments'] = instruments.copy()
    
    def get_instruments(self, exchange: Optional[str] = None, 
                       instrument_type: Optional[str] = None) -> pd.DataFrame:
        """Get instrument data from memory."""
        df = self._data['instruments'].copy()
        
        if df.empty:
            return df
        
        if exchange:
            df = df[df['exchange'] == exchange]
        
        if instrument_type:
            df = df[df['instrument_type'] == instrument_type]
        
        return df
    
    def get_instrument_by_token(self, instrument_token: int) -> Optional[Dict[str, Any]]:
        """Get single instrument by token."""
        df = self._data['instruments']
        
        if df.empty:
            return None
        
        matches = df[df['instrument_token'] == instrument_token]
        
        if matches.empty:
            return None
        
        return matches.iloc[0].to_dict()
    
    def search_instruments(self, query: str) -> pd.DataFrame:
        """Search instruments by symbol or name."""
        df = self._data['instruments']
        
        if df.empty:
            return df
        
        query_lower = query.lower()
        
        mask = (
            df['tradingsymbol'].str.lower().str.contains(query_lower, na=False) |
            df['name'].str.lower().str.contains(query_lower, na=False)
        )
        
        return df[mask]


class MemoryPortfolioStorage(PortfolioStorage, MemoryStorage):
    """In-memory storage for portfolio data."""
    
    def connect(self) -> bool:
        """Establish connection (no-op for memory storage)."""
        return True
    
    def disconnect(self) -> bool:
        """Close connection (no-op for memory storage)."""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return {
            'status': 'healthy',
            'type': 'memory',
            'position_count': len(self._data['positions']),
            'holding_count': len(self._data['holdings'])
        }
    
    def store_positions(self, positions: List[Position]) -> int:
        """Store position data."""
        self.save_positions(positions)
        return len(positions)
    
    def store_holdings(self, holdings: List[Holding]) -> int:
        """Store holdings data."""
        self.save_holdings(holdings)
        return len(holdings)
    
    def get_positions_history(self, from_date: date, to_date: date) -> List[Position]:
        """Get position history (simple implementation for memory storage)."""
        return self.get_positions()  # Memory storage doesn't track history
    
    def calculate_pnl_history(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Calculate P&L history (simple implementation for memory storage)."""
        positions = self.get_positions()
        total_pnl = sum(getattr(pos, 'pnl', 0) for pos in positions if symbol is None or pos.tradingsymbol == symbol)
        return {
            'total_pnl': total_pnl,
            'positions': len(positions),
            'symbol': symbol
        }
    
    def save_positions(self, positions: List[Position]) -> None:
        """Save position data to memory."""
        self._data['positions'] = positions.copy()
    
    def get_positions(self) -> List[Position]:
        """Get all positions from memory."""
        return self._data['positions'].copy()
    
    def save_holdings(self, holdings: List[Holding]) -> None:
        """Save holding data to memory."""
        self._data['holdings'] = holdings.copy()
    
    def get_holdings(self) -> List[Holding]:
        """Get all holdings from memory."""
        return self._data['holdings'].copy()
    
    def get_position_by_symbol(self, tradingsymbol: str, 
                              product: Optional[str] = None) -> Optional[Position]:
        """Get position by trading symbol."""
        for position in self._data['positions']:
            if position.tradingsymbol == tradingsymbol:
                if product is None or position.product == product:
                    return position
        return None
    
    def get_holding_by_symbol(self, tradingsymbol: str) -> Optional[Holding]:
        """Get holding by trading symbol."""
        for holding in self._data['holdings']:
            if holding.tradingsymbol == tradingsymbol:
                return holding
        return None


class MemorySessionStorage(BaseStorage):
    """In-memory storage for session data."""
    
    def __init__(self):
        self._sessions = {}
    
    def connect(self) -> bool:
        """Establish connection (no-op for memory storage)."""
        return True
    
    def disconnect(self) -> bool:
        """Close connection (no-op for memory storage)."""
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return {
            'status': 'healthy',
            'type': 'memory',
            'session_count': len(self._sessions)
        }
    
    def save_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data."""
        self._sessions[user_id] = {
            **session_data,
            'updated_at': datetime.now()
        }
    
    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self._sessions.get(user_id)
    
    def delete_session(self, user_id: str) -> None:
        """Delete session data."""
        self._sessions.pop(user_id, None)
    
    def clear_sessions(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()


# Convenience factory function
def create_memory_storage() -> Dict[str, Any]:
    """Create all memory storage implementations.
    
    Returns:
        Dictionary with storage implementations
    """
    return {
        'candles': MemoryCandleStorage(),
        'ticks': MemoryTickStorage(),
        'instruments': MemoryInstrumentStorage(),
        'portfolio': MemoryPortfolioStorage(),
        'sessions': MemorySessionStorage(),
    }