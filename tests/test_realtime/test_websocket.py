"""Unit tests for KiteWebSocket."""

import pytest
from unittest.mock import MagicMock, patch
from lib_zerodha.realtime.kite_websocket import KiteWebSocket
from lib_zerodha.models.market_data import Tick

class TestKiteWebSocket:
    def test_init(self):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        assert ws.api_key == "api_key"
        assert ws.access_token == "access_token"
        assert not ws.is_connected

    def test_get_url(self):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        url = ws._get_url()
        assert "api_key=api_key" in url
        assert "access_token=access_token" in url

    @patch('websocket.WebSocketApp')
    def test_connect(self, mock_ws_app):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        ws.connect(threaded=False)
        mock_ws_app.assert_called_once()
        # Verify run_forever was called
        mock_ws_app.return_value.run_forever.assert_called_once()

    def test_on_tick_registration(self):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        handler = MagicMock()
        ws.on_tick(handler)
        assert handler in ws._on_tick_handlers

    def test_parse_binary_empty(self):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        ticks = ws._parse_binary(b"")
        assert ticks == []

    def test_parse_packet_too_short(self):
        ws = KiteWebSocket(api_key="api_key", access_token="access_token")
        tick = ws._parse_packet(b"\x00\x00\x00")
        assert tick is None
