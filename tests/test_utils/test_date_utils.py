"""Unit tests for date_utils."""

import pytest
from datetime import datetime, date, time
import pytz
from lib_zerodha.utils.date_utils import now_ist, to_ist, is_market_day, is_market_open, IST

class TestDateUtils:
    def test_now_ist(self):
        dt = now_ist()
        assert dt.tzinfo.zone == 'Asia/Kolkata'

    def test_to_ist(self):
        dt_utc = datetime(2024, 1, 1, 10, 0, 0, tzinfo=pytz.UTC)
        dt_ist = to_ist(dt_utc)
        assert dt_ist.hour == 15
        assert dt_ist.minute == 30

    def test_is_market_day(self):
        # Monday
        assert is_market_day(date(2024, 1, 1)) is True
        # Sunday
        assert is_market_day(date(2024, 1, 7)) is False

    def test_is_market_open(self):
        # 10 AM on a Monday
        dt = IST.localize(datetime(2024, 1, 1, 10, 0, 0))
        assert is_market_open(dt) is True
        
        # 8 AM on a Monday
        dt = IST.localize(datetime(2024, 1, 1, 8, 0, 0))
        assert is_market_open(dt) is False
        
        # 10 AM on a Sunday
        dt = IST.localize(datetime(2024, 1, 7, 10, 0, 0))
        assert is_market_open(dt) is False
        
        # 4 PM on a Monday
        dt = IST.localize(datetime(2024, 1, 1, 16, 0, 0))
        assert is_market_open(dt) is False
