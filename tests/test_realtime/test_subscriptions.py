"""Unit tests for SubscriptionManager."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from lib_zerodha.realtime.subscriptions import SubscriptionManager
from lib_zerodha.realtime.kite_websocket import KiteWebSocket
from lib_zerodha.models.market_data import Tick

class TestSubscriptionManager:
    @pytest.fixture
    def mock_ws(self):
        ws = MagicMock(spec=KiteWebSocket)
        ws.is_connected = True
        return ws

    @pytest.fixture
    def manager(self, mock_ws):
        return SubscriptionManager(mock_ws)

    def test_subscribe(self, manager, mock_ws):
        manager.subscribe([1, 2], mode="full", group_name="test_group")
        
        mock_ws.subscribe.assert_called_once_with([1, 2], "full")
        assert manager.is_subscribed(1)
        assert manager.is_subscribed(2)
        assert 1 in manager.get_subscription_groups()["test_group"]

    def test_unsubscribe(self, manager, mock_ws):
        manager.subscribe([1], mode="ltp")
        manager.unsubscribe([1])
        
        mock_ws.unsubscribe.assert_called_once_with([1])
        assert not manager.is_subscribed(1)

    def test_handle_ticks(self, manager):
        tick = Tick(instrument_token=1, timestamp=datetime.now(), last_price=100.0, volume=10, average_price=100.0)
        callback = Mock()
        manager.on_tick(callback)
        
        manager._handle_ticks([tick])
        callback.assert_called_once_with(tick)
        assert manager._last_tick_time is not None
