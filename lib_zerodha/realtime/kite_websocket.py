"""WebSocket client for Kite Connect real-time data."""

import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any, Union
import websocket
import struct
import logging

from ..config import config
from ..exceptions.api_exceptions import WebSocketError, ConnectionError, SubscriptionError
from ..models.market_data import Tick

logger = logging.getLogger(__name__)

class KiteWebSocket:
    """Robust WebSocket client for Kite Connect.
    
    Implements dynamic binary parsing and exponential backoff reconnection.
    """
    
    MODE_LTP = "ltp"
    MODE_QUOTE = "quote"
    MODE_FULL = "full"
    
    def __init__(self, api_key: str, access_token: str, user_id: str = None,
                 public_token: str = None, config_obj: Optional[object] = None):
        self.api_key = api_key
        self.access_token = access_token
        self.user_id = user_id
        self.public_token = public_token
        self.config = config_obj or config
        
        self._ws = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        
        self._subscriptions = {}  # token -> mode
        
        # Event handlers
        self._on_tick_handlers = []
        self._on_error_handlers = []
        self._on_connect_handlers = []
        self._on_close_handlers = []
        
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected

    def _get_url(self):
        return f"{self.config.websocket_url}?api_key={self.api_key}&access_token={self.access_token}"

    def _on_message(self, ws, message):
        if not isinstance(message, bytes):
            return
            
        try:
            ticks = self._parse_binary(message)
            for handler in self._on_tick_handlers:
                try:
                    handler(ticks)
                except Exception as e:
                    logger.error(f"Error in tick handler: {e}")
        except Exception as e:
            self._handle_error(f"Tick processing failed: {e}")

    def _parse_binary(self, data: bytes) -> List[Tick]:
        ticks = []
        offset = 0
        
        while offset < len(data):
            if offset + 2 > len(data): break
            
            packet_len = struct.unpack(">H", data[offset:offset+2])[0]
            offset += 2
            
            if offset + packet_len > len(data): break
            
            packet = data[offset:offset+packet_len]
            tick = self._parse_packet(packet)
            if tick:
                ticks.append(tick)
            
            offset += packet_len
            
        return ticks

    def _parse_packet(self, data: bytes) -> Optional[Tick]:
        if len(data) < 4: return None
        
        token = struct.unpack(">I", data[0:4])[0]
        mode = self._subscriptions.get(token, self.MODE_LTP)
        
        try:
            if mode == self.MODE_LTP and len(data) >= 8:
                lp = struct.unpack(">I", data[4:8])[0] / 100.0
                return Tick.from_dict({'instrument_token': token, 'last_price': lp})
            
            elif mode == self.MODE_QUOTE and len(data) >= 44:
                # Basic quote parsing
                lp = struct.unpack(">I", data[4:8])[0] / 100.0
                vol = struct.unpack(">I", data[16:20])[0]
                return Tick.from_dict({'instrument_token': token, 'last_price': lp, 'volume': vol})
                
            # Full mode parsing can be expanded here
            
        except Exception as e:
            logger.debug(f"Parsing failed for {token}: {e}")
            
        return None

    def _attempt_reconnect(self):
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnect reached")
            return

        self._reconnect_attempts += 1
        delay = min(2 ** self._reconnect_attempts, 60)
        logger.info(f"Reconnecting in {delay} seconds...")
        
        def backoff():
            time.sleep(delay)
            self.connect()
            
        threading.Thread(target=backoff, daemon=True).start()

    def connect(self, threaded: bool = True):
        """Connect to WebSocket."""
        with self._lock:
            if self._connected: return
            
        self._ws = websocket.WebSocketApp(
            self._get_url(),
            on_message=self._on_message,
            on_open=self._on_open_callback,
            on_close=self._on_close_callback,
            on_error=lambda ws, err: self._handle_error(str(err))
        )
        
        if threaded:
            t = threading.Thread(target=self._ws.run_forever, kwargs={'ping_interval': 30})
            t.daemon = True
            t.start()
        else:
            self._ws.run_forever(ping_interval=30)

    def disconnect(self):
        """Disconnect WebSocket."""
        if self._ws:
            self._ws.close()

    def _on_open_callback(self, ws):
        self._connected = True
        self._reconnect_attempts = 0
        logger.info("WebSocket connected")
        
        # Resubscribe to existing tokens if any
        with self._lock:
            for token, mode in self._subscriptions.items():
                # We need to send subscribe for each mode group or just resubscribe all
                # This is a simplified resubscribe
                pass # Logic to resubscribe would go here

        for handler in self._on_connect_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error in connect handler: {e}")

    def _on_close_callback(self, ws, close_status_code, close_msg):
        self._connected = False
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        for handler in self._on_close_handlers:
            try:
                handler(close_status_code, close_msg)
            except Exception as e:
                logger.error(f"Error in close handler: {e}")
                
        self._attempt_reconnect()

    def _handle_error(self, msg):
        logger.error(f"WebSocket error: {msg}")
        err = WebSocketError(msg)
        for h in self._on_error_handlers:
            try:
                h(err)
            except Exception:
                pass

    def subscribe(self, tokens: List[int], mode: str = MODE_LTP):
        """Subscribe to tokens with a specific mode."""
        with self._lock:
            for t in tokens: 
                self._subscriptions[t] = mode
        
        if self._connected:
            self._ws.send(json.dumps({"a": "subscribe", "v": tokens}))
            if mode != self.MODE_LTP:
                self._ws.send(json.dumps({"a": "mode", "v": tokens, "m": mode}))

    def unsubscribe(self, tokens: List[int]):
        """Unsubscribe from tokens."""
        with self._lock:
            for t in tokens:
                self._subscriptions.pop(t, None)
                
        if self._connected:
            self._ws.send(json.dumps({"a": "unsubscribe", "v": tokens}))

    def set_mode(self, tokens: List[int], mode: str):
        """Set mode for tokens."""
        with self._lock:
            for t in tokens:
                if t in self._subscriptions:
                    self._subscriptions[t] = mode
                    
        if self._connected:
            self._ws.send(json.dumps({"a": "mode", "v": tokens, "m": mode}))

    # Handler registration methods
    def on_tick(self, handler: Callable[[List[Tick]], None]):
        """Register a tick handler."""
        self._on_tick_handlers.append(handler)

    def on_error(self, handler: Callable[[Exception], None]):
        """Register an error handler."""
        self._on_error_handlers.append(handler)
        
    def on_connect(self, handler: Callable[[], None]):
        """Register a connect handler."""
        self._on_connect_handlers.append(handler)
        
    def on_close(self, handler: Callable[[int, str], None]):
        """Register a close handler."""
        self._on_close_handlers.append(handler)