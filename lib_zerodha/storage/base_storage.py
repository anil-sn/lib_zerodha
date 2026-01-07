"""Abstract storage interface for lib_zerodha."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import pandas as pd

from ..models.market_data import HistoricalData, Tick
from ..models.portfolio import Position, Holding
from ..models.base import Instrument


class BaseStorage(ABC):
    """Abstract base class for storage implementations."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to storage.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Close connection to storage.
        
        Returns:
            True if disconnection successful
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check storage health and performance.
        
        Returns:
            Dictionary with health metrics
        """
        pass


class CandleStorage(BaseStorage):
    """Abstract interface for candle/OHLCV data storage."""
    
    @abstractmethod
    def store_candle(self,
                    instrument_token: int,
                    interval: str,
                    candle_data: HistoricalData) -> bool:
        """Store single candle data.
        
        Args:
            instrument_token: Instrument token
            interval: Candle interval (1m, 5m, 1d, etc.)
            candle_data: HistoricalData object
            
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    def store_candles_batch(self,
                           instrument_token: int,
                           interval: str,
                           candles: List[HistoricalData]) -> int:
        """Store multiple candles in batch.
        
        Args:
            instrument_token: Instrument token
            interval: Candle interval
            candles: List of HistoricalData objects
            
        Returns:
            Number of candles stored
        """
        pass
    
    @abstractmethod
    def get_candles(self,
                   instrument_token: int,
                   interval: str,
                   start_date: datetime,
                   end_date: datetime) -> pd.DataFrame:
        """Retrieve candles for date range.
        
        Args:
            instrument_token: Instrument token
            interval: Candle interval
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            DataFrame with OHLCV data
        """
        pass
    
    @abstractmethod
    def get_latest_candle(self,
                         instrument_token: int,
                         interval: str) -> Optional[HistoricalData]:
        """Get most recent candle.
        
        Args:
            instrument_token: Instrument token
            interval: Candle interval
            
        Returns:
            Latest HistoricalData or None
        """
        pass
    
    @abstractmethod
    def delete_old_candles(self,
                          instrument_token: int,
                          interval: str,
                          before_date: datetime) -> int:
        """Delete old candles before specified date.
        
        Args:
            instrument_token: Instrument token
            interval: Candle interval
            before_date: Delete candles before this date
            
        Returns:
            Number of candles deleted
        """
        pass


class TickStorage(BaseStorage):
    """Abstract interface for tick data storage."""
    
    @abstractmethod
    def store_tick(self, tick: Tick) -> bool:
        """Store single tick data.
        
        Args:
            tick: Tick object
            
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    def store_ticks_batch(self, ticks: List[Tick]) -> int:
        """Store multiple ticks in batch.
        
        Args:
            ticks: List of Tick objects
            
        Returns:
            Number of ticks stored
        """
        pass
    
    @abstractmethod
    def get_ticks(self,
                 instrument_token: int,
                 start_time: datetime,
                 end_time: datetime) -> List[Tick]:
        """Retrieve ticks for time range.
        
        Args:
            instrument_token: Instrument token
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            List of Tick objects
        """
        pass
    
    @abstractmethod
    def get_latest_tick(self, instrument_token: int) -> Optional[Tick]:
        """Get most recent tick.
        
        Args:
            instrument_token: Instrument token
            
        Returns:
            Latest Tick or None
        """
        pass


class InstrumentStorage(BaseStorage):
    """Abstract interface for instrument metadata storage."""
    
    @abstractmethod
    def store_instruments(self, instruments: List[Instrument]) -> int:
        """Store instrument metadata.
        
        Args:
            instruments: List of Instrument objects
            
        Returns:
            Number of instruments stored
        """
        pass
    
    @abstractmethod
    def get_instrument(self, instrument_token: int) -> Optional[Instrument]:
        """Get instrument by token.
        
        Args:
            instrument_token: Instrument token
            
        Returns:
            Instrument object or None
        """
        pass
    
    @abstractmethod
    def search_instruments(self,
                          symbol: Optional[str] = None,
                          exchange: Optional[str] = None,
                          instrument_type: Optional[str] = None) -> List[Instrument]:
        """Search instruments by criteria.
        
        Args:
            symbol: Symbol pattern to search
            exchange: Exchange filter
            instrument_type: Instrument type filter
            
        Returns:
            List of matching Instrument objects
        """
        pass


class PortfolioStorage(BaseStorage):
    """Abstract interface for portfolio data storage."""
    
    @abstractmethod
    def store_positions(self, positions: List[Position], date: date) -> bool:
        """Store position data.
        
        Args:
            positions: List of Position objects
            date: Trading date
            
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    def store_holdings(self, holdings: List[Holding], date: date) -> bool:
        """Store holdings data.
        
        Args:
            holdings: List of Holding objects
            date: Date
            
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    def get_positions_history(self,
                             start_date: date,
                             end_date: date) -> Dict[date, List[Position]]:
        """Get historical positions.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary mapping dates to position lists
        """
        pass
    
    @abstractmethod
    def calculate_pnl_history(self,
                             start_date: date,
                             end_date: date) -> pd.DataFrame:
        """Calculate P&L history.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with P&L metrics over time
        """
        pass