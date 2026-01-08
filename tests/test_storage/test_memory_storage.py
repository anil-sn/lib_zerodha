"""Unit tests for MemoryTickStorage."""

import pytest
from datetime import datetime
from lib_zerodha.storage.memory_storage import MemoryTickStorage
from lib_zerodha.models.market_data import Tick

class TestMemoryStorage:
    def test_init(self):
        storage = MemoryTickStorage()
        assert storage.connect() is True

    def test_save_and_get_ticks(self):
        storage = MemoryTickStorage()
        ts = datetime.now()
        tick = Tick(instrument_token=1, timestamp=ts, last_price=100.0, volume=10, average_price=100.0)
        
        storage.save_ticks([tick])
        ticks = storage.get_ticks(1, ts, ts)
        assert len(ticks) == 1
        assert ticks[0].last_price == 100.0

    def test_clear_ticks(self):
        storage = MemoryTickStorage()
        tick = Tick(instrument_token=1, timestamp=datetime.now(), last_price=100.0, volume=10, average_price=100.0)
        storage.save_ticks([tick])
        
        storage.clear()
        assert len(storage.get_ticks(1, datetime.min, datetime.max)) == 0