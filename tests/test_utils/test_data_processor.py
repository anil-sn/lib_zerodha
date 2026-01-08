"""Unit tests for DataProcessor."""

import pytest
from datetime import datetime
from lib_zerodha.utils.data_processor import DataProcessor
from lib_zerodha.models.base import OHLC

class TestDataProcessor:
    def test_init(self):
        dp = DataProcessor()
        assert dp is not None

    def test_process_tick(self):
        dp = DataProcessor()
        ts = datetime.now()
        tick = {
            'instrument_token': 1,
            'timestamp': ts,
            'last_price': 100.0,
            'volume': 10
        }
        
        dp.process_tick(tick)
        
        # Check current building candle
        candle = dp.current_candles['1minute'][1]
        assert candle.open == 100.0
        assert candle.tick_count == 1
        
        # Check quote cache
        quote = dp.get_latest_quote(1)
        assert quote is not None
        assert quote.last_price == 100.0

    def test_candle_completion(self):
        dp = DataProcessor()
        ts1 = datetime.now()
        # Mock candle timestamp to be different so it completes
        ts2 = ts1.replace(minute=(ts1.minute + 1) % 60)
        
        dp.process_tick({'instrument_token': 1, 'timestamp': ts1, 'last_price': 100, 'volume': 10})
        dp.process_tick({'instrument_token': 1, 'timestamp': ts2, 'last_price': 105, 'volume': 20})
        
        candles = dp.get_candles(1, '1minute')
        assert len(candles) >= 1