"""Unit tests for ZerodhaWebSocketManager."""

import pytest
from unittest.mock import MagicMock, patch
from lib_zerodha.realtime.websocket_manager import ZerodhaWebSocketManager

class TestWebSocketManager:
    @patch('lib_zerodha.realtime.websocket_manager.KiteWebSocket')
    def test_init(self, mock_ws):
        manager = ZerodhaWebSocketManager(api_key="api_key", access_token="access_token")
        assert manager.api_key == "api_key"
        assert manager.access_token == "access_token"

    @patch('lib_zerodha.realtime.websocket_manager.KiteWebSocket')
    @patch('threading.Thread')
    def test_subscribe(self, mock_thread, mock_ws_class):
        mock_ws = MagicMock()
        mock_ws_class.return_value = mock_ws
        
        manager = ZerodhaWebSocketManager(api_key="api_key", access_token="access_token")
        manager.subscribe([1, 2], mode="quote")
        
        assert 0 in manager.connections
        mock_ws.subscribe.assert_called()
        mock_ws.set_mode.assert_called()
