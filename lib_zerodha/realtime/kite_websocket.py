"""WebSocket client for Kite Connect real-time data."""

import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any
import websocket
import struct

from ..config import config
from ..exceptions.api_exceptions import WebSocketError, ConnectionError, SubscriptionError
from ..models.market_data import Tick


class KiteWebSocket:
    """WebSocket client for Kite Connect real-time data streams.
    
    Handles connection management, subscription management,
    and real-time tick data processing.
    """
    
    # Message modes
    MODE_LTP = "ltp"  # Last traded price
    MODE_QUOTE = "quote"  # Quote with bid/ask
    MODE_FULL = "full"  # Full market depth
    
    def __init__(self, api_key: str, access_token: str, user_id: str,
                 public_token: str, config_obj: Optional[object] = None):
        """Initialize WebSocket client.
        
        Args:
            api_key: Kite Connect API key
            access_token: Access token
            user_id: User ID
            public_token: Public token
            config: Configuration manager
        """
        self.api_key = api_key
        self.access_token = access_token
        self.user_id = user_id
        self.public_token = public_token
        self.config = config_obj or config
        
        # WebSocket connection
        self._ws = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 1  # seconds
        
        # Subscriptions
        self._subscriptions = {}  # instrument_token -> mode
        
        # Event handlers
        self._on_tick_handlers = []
        self._on_connect_handlers = []
        self._on_disconnect_handlers = []
        self._on_error_handlers = []
        
        # Threading
        self._lock = threading.RLock()
    
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL."""
        base_url = self.config.websocket_url
        return f"{base_url}?api_key={self.api_key}&access_token={self.access_token}"
    
    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        with self._lock:
            self._connected = True
            self._reconnect_attempts = 0
        
        # Restore subscriptions
        if self._subscriptions:
            self._restore_subscriptions()
        
        # Notify handlers
        for handler in self._on_connect_handlers:
            try:
                handler()
            except Exception as e:
                self._handle_error(f"Error in connect handler: {e}")
    
    def _on_message(self, ws, message):
        """Handle WebSocket message received."""
        try:
            # Parse binary tick data
            ticks = self._parse_binary_data(message)
            
            # Notify tick handlers
            for handler in self._on_tick_handlers:
                try:
                    handler(ticks)
                except Exception as e:
                    self._handle_error(f"Error in tick handler: {e}")
                    
        except Exception as e:
            self._handle_error(f"Error processing message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        self._handle_error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        with self._lock:
            self._connected = False
        
        # Notify handlers
        for handler in self._on_disconnect_handlers:
            try:
                handler()
            except Exception as e:
                self._handle_error(f"Error in disconnect handler: {e}")
        
        # Attempt reconnection
        self._attempt_reconnection()
    
    def _parse_binary_data(self, data: bytes) -> List[Tick]:
        """Parse binary tick data from WebSocket.
        
        Args:
            data: Binary data from WebSocket
            
        Returns:
            List of parsed ticks
        """
        ticks = []
        offset = 0
        
        while offset < len(data):
            try:
                # Read packet length (first 2 bytes)
                if offset + 2 > len(data):
                    break
                    
                packet_length = struct.unpack(">H", data[offset:offset + 2])[0]
                offset += 2
                
                if offset + packet_length > len(data):
                    break
                
                # Extract packet data
                packet_data = data[offset:offset + packet_length]
                offset += packet_length
                
                # Parse tick from packet
                tick = self._parse_tick_packet(packet_data)
                if tick:
                    ticks.append(tick)
                    
            except Exception as e:
                self._handle_error(f"Error parsing tick data: {e}")
                break
        
        return ticks
    
    def _parse_tick_packet(self, data: bytes) -> Optional[Tick]:
        """Parse individual tick packet.
        
        Args:
            data: Packet data
            
        Returns:
            Parsed tick or None
        """
        try:
            if len(data) < 8:
                return None
            
            # Parse instrument token (first 4 bytes)
            instrument_token = struct.unpack(">I", data[0:4])[0]
            
            # Get subscription mode
            mode = self._subscriptions.get(instrument_token, self.MODE_LTP)
            
            # Parse based on mode
            if mode == self.MODE_LTP:
                return self._parse_ltp_data(instrument_token, data)
            elif mode == self.MODE_QUOTE:
                return self._parse_quote_data(instrument_token, data)
            elif mode == self.MODE_FULL:
                return self._parse_full_data(instrument_token, data)
                
        except Exception as e:
            self._handle_error(f"Error parsing tick packet: {e}")
            return None
    
    def _parse_ltp_data(self, instrument_token: int, data: bytes) -> Optional[Tick]:
        """Parse LTP mode data."""
        if len(data) < 8:
            return None
        
        # LTP is at offset 4-8
        last_price = struct.unpack(">I", data[4:8])[0] / 100.0
        
        return Tick(
            instrument_token=instrument_token,
            timestamp=datetime.now(),
            last_price=last_price
        )
    
    def _parse_quote_data(self, instrument_token: int, data: bytes) -> Optional[Tick]:
        """Parse quote mode data."""
        if len(data) < 44:
            return None
        
        # Parse quote data
        last_price = struct.unpack(">I", data[4:8])[0] / 100.0
        last_quantity = struct.unpack(">I", data[8:12])[0]
        average_price = struct.unpack(">I", data[12:16])[0] / 100.0
        volume = struct.unpack(">I", data[16:20])[0]
        buy_quantity = struct.unpack(">I", data[20:24])[0]
        sell_quantity = struct.unpack(">I", data[24:28])[0]
        open_price = struct.unpack(">I", data[28:32])[0] / 100.0
        high_price = struct.unpack(">I", data[32:36])[0] / 100.0
        low_price = struct.unpack(">I", data[36:40])[0] / 100.0
        close_price = struct.unpack(">I", data[40:44])[0] / 100.0
        
        return Tick(
            instrument_token=instrument_token,
            timestamp=datetime.now(),
            last_price=last_price,
            last_quantity=last_quantity,
            average_price=average_price,
            volume=volume,
            buy_quantity=buy_quantity,
            sell_quantity=sell_quantity,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price
        )
    
    def _parse_full_data(self, instrument_token: int, data: bytes) -> Optional[Tick]:
        """Parse full mode data with market depth."""
        # Full mode parsing is more complex
        # For now, fall back to quote parsing
        return self._parse_quote_data(instrument_token, data)
    
    def _restore_subscriptions(self):
        """Restore subscriptions after reconnection."""
        if not self._subscriptions:
            return
        
        try:
            # Group by mode
            mode_groups = {}
            for instrument_token, mode in self._subscriptions.items():
                if mode not in mode_groups:
                    mode_groups[mode] = []
                mode_groups[mode].append(instrument_token)
            
            # Subscribe for each mode
            for mode, tokens in mode_groups.items():
                self._send_subscription_message(tokens, mode, "subscribe")
                
        except Exception as e:
            self._handle_error(f"Error restoring subscriptions: {e}")
    
    def _send_subscription_message(self, instrument_tokens: List[int], 
                                 mode: str, action: str):
        """Send subscription message to WebSocket."""
        if not self._connected or not self._ws:
            raise ConnectionError("WebSocket not connected")
        
        message = {
            "a": action,  # subscribe/unsubscribe
            "v": instrument_tokens
        }
        
        # Set mode
        if mode == self.MODE_QUOTE:
            message["m"] = "quote"
        elif mode == self.MODE_FULL:
            message["m"] = "full"
        # LTP is default, no mode needed
        
        try:
            self._ws.send(json.dumps(message))
        except Exception as e:
            raise SubscriptionError(f"Failed to send subscription: {e}")
    
    def _attempt_reconnection(self):
        """Attempt to reconnect WebSocket."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._handle_error("Maximum reconnection attempts reached")
            return
        
        self._reconnect_attempts += 1
        time.sleep(self._reconnect_delay * self._reconnect_attempts)
        
        try:
            self.connect()
        except Exception as e:
            self._handle_error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
    
    def _handle_error(self, error_message: str):
        """Handle error and notify handlers."""
        error = WebSocketError(error_message)
        
        for handler in self._on_error_handlers:
            try:
                handler(error)
            except Exception:
                pass  # Don't let handler errors break error handling
    
    # Public API
    def connect(self):
        """Connect to WebSocket."""
        if self._connected:
            return
        
        try:
            websocket.enableTrace(False)
            self._ws = websocket.WebSocketApp(
                self._get_websocket_url(),
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in a separate thread
            self._ws_thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={'ping_interval': 30, 'ping_timeout': 10}
            )
            self._ws_thread.daemon = True
            self._ws_thread.start()
            
            # Wait for connection
            for _ in range(50):  # 5 second timeout
                if self._connected:
                    break
                time.sleep(0.1)
            
            if not self._connected:
                raise ConnectionError("Failed to connect within timeout")
                
        except Exception as e:
            raise ConnectionError(f"Failed to connect WebSocket: {e}")
    
    def disconnect(self):
        """Disconnect from WebSocket."""
        with self._lock:
            if self._ws:
                self._ws.close()
                self._ws = None
            self._connected = False
    
    def subscribe(self, instrument_tokens: List[int], mode: str = MODE_LTP):
        """Subscribe to instruments.
        
        Args:
            instrument_tokens: List of instrument tokens
            mode: Subscription mode (ltp, quote, full)
        """
        if not instrument_tokens:
            return
        
        # Update subscriptions
        for token in instrument_tokens:
            self._subscriptions[token] = mode
        
        # Send subscription if connected
        if self._connected:
            self._send_subscription_message(instrument_tokens, mode, "subscribe")
    
    def unsubscribe(self, instrument_tokens: List[int]):
        """Unsubscribe from instruments."""
        if not instrument_tokens:
            return
        
        # Remove from subscriptions
        for token in instrument_tokens:
            self._subscriptions.pop(token, None)
        
        # Send unsubscribe if connected
        if self._connected:
            # Group by mode for unsubscription
            mode_groups = {}
            for token in instrument_tokens:
                # Use LTP as default for unsubscription
                mode = self.MODE_LTP
                if mode not in mode_groups:
                    mode_groups[mode] = []
                mode_groups[mode].append(token)
            
            for mode, tokens in mode_groups.items():
                self._send_subscription_message(tokens, mode, "unsubscribe")
    
    def set_mode(self, instrument_tokens: List[int], mode: str):
        """Set subscription mode for instruments."""
        # Unsubscribe first
        self.unsubscribe(instrument_tokens)
        # Subscribe with new mode
        self.subscribe(instrument_tokens, mode)
    
    # Event handlers
    def on_tick(self, callback: Callable[[List[Tick]], None]):
        """Register tick event handler."""
        self._on_tick_handlers.append(callback)
    
    def on_connect(self, callback: Callable[[], None]):
        """Register connect event handler."""
        self._on_connect_handlers.append(callback)
    
    def on_disconnect(self, callback: Callable[[], None]):
        """Register disconnect event handler."""
        self._on_disconnect_handlers.append(callback)
    
    def on_error(self, callback: Callable[[Exception], None]):
        """Register error event handler."""
        self._on_error_handlers.append(callback)
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    @property
    def subscribed_instruments(self) -> Dict[int, str]:
        """Get currently subscribed instruments."""
        return self._subscriptions.copy()