"""Unit tests for TickAggregator and MarketDepthProcessor."""

import pytest
from datetime import datetime
from lib_zerodha.realtime.data_handlers import TickAggregator, MarketDepthProcessor
from lib_zerodha.models.market_data import Tick

class TestDataHandlers:
    def test_tick_aggregator_basic(self):
        agg = TickAggregator(interval_seconds=60)
        ts = datetime(2024, 1, 1, 10, 0, 0)
        
        tick1 = Tick(instrument_token=1, timestamp=ts, last_price=100.0, volume=10, average_price=100.0)
        agg.process_tick(tick1)
        
        candle = agg.get_current_candle(1)
        assert candle['open'] == 100.0
        assert candle['high'] == 100.0
        assert candle['tick_count'] == 1
        
        tick2 = Tick(instrument_token=1, timestamp=ts, last_price=110.0, volume=20, average_price=105.0)
        agg.process_tick(tick2)
        
        candle = agg.get_current_candle(1)
        assert candle['high'] == 110.0
        assert candle['tick_count'] == 2

    def test_tick_aggregator_completion(self):
        agg = TickAggregator(interval_seconds=60)
        ts1 = datetime(2024, 1, 1, 10, 0, 0)
        ts2 = datetime(2024, 1, 1, 10, 1, 0) # Next minute
        
        tick1 = Tick(instrument_token=1, timestamp=ts1, last_price=100.0, volume=10, average_price=100.0)
        agg.process_tick(tick1)
        
        tick2 = Tick(instrument_token=1, timestamp=ts2, last_price=105.0, volume=20, average_price=102.5)
        agg.process_tick(tick2) # This completes the first candle
        
        history = agg.get_candle_history(1)
        assert len(history) == 1
        assert history[0]['timestamp'] == ts1
        assert history[0]['close'] == 100.0

    def test_market_depth_processor(self):
        proc = MarketDepthProcessor()
        ts = datetime(2024, 1, 1, 10, 0, 0)
        depth = {'buy': [{'price': 99.0, 'quantity': 100}], 'sell': [{'price': 101.0, 'quantity': 100}]}
        
        tick = Tick(instrument_token=1, timestamp=ts, last_price=100.0, volume=10, average_price=100.0)
        tick.depth = depth
        
        proc.process_tick(tick)
        result = proc.get_market_depth(1)
        assert result['buy'] == depth['buy']
        assert result['sell'] == depth['sell']
