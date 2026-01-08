"""Unit tests for InMemoryCandleStore."""

import pytest
from datetime import datetime
from lib_zerodha.realtime.candle_store import InMemoryCandleStore
from lib_zerodha.models.market_data import Tick

class TestCandleStore:
    def test_add_tick_and_get_candles(self):
        store = InMemoryCandleStore()
        ts = datetime(2024, 1, 1, 10, 0, 0)
        tick = Tick(instrument_token=1, timestamp=ts, last_price=100.0, volume=10, average_price=100.0)
        
        store.add_tick(tick)
        
        # Current candle for 1minute
        candles = store.get_candles(1, "1minute", include_incomplete=True)
        assert len(candles) == 1
        assert candles[0]['open'] == 100.0
        
    def test_candle_completion(self):
        store = InMemoryCandleStore()
        ts1 = datetime(2024, 1, 1, 10, 0, 0)
        ts2 = datetime(2024, 1, 1, 10, 1, 0) # Next minute
        
        tick1 = Tick(instrument_token=1, timestamp=ts1, last_price=100.0, volume=10, average_price=100.0)
        store.add_tick(tick1)
        
        tick2 = Tick(instrument_token=1, timestamp=ts2, last_price=105.0, volume=20, average_price=102.5)
        store.add_tick(tick2) # Completes first candle
        
        candles = store.get_candles(1, "1minute")
        assert len(candles) == 1
        assert candles[0]['timestamp'] == ts1
        assert candles[0]['close'] == 100.0
