"""Kite Connect WebSocket client for real-time data."""

import websocket
import json
import struct
import threading
import time
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import logging

from .config import config
from .exceptions import WebSocketError, AuthenticationError
from .data_models import Quote, OHLC

logger = logging.getLogger(__name__)

class KiteWebSocketClient:
    """WebSocket client for real-time market data."""
    
    # WebSocket modes
    MODE_LTP = "ltp"
    MODE_QUOTE = "quote"
    MODE_FULL = "full"
    
    def __init__(self, api_key: str, access_token: str, 
                 on_tick: Callable = None, on_connect: Callable = None,
                 on_close: Callable = None, on_error: Callable = None):
        self.api_key = api_key
        self.access_token = access_token
        self.ws_url = f"{config.websocket_url}?api_key={api_key}&access_token={access_token}"
        
        # Callbacks
        self.on_tick = on_tick
        self.on_connect = on_connect
        self.on_close = on_close
        self.on_error = on_error
        
        # WebSocket instance
        self.ws = None
        self.is_connected = False
        
        # Subscriptions
        self.subscribed_tokens = set()
        self.token_modes = {}  # token -> mode mapping
        
        # Threading
        self._stop_event = threading.Event()
        self._heartbeat_thread = None
    
    def connect(self, threaded: bool = True) -> None:
        """Connect to WebSocket."""
        try:
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            if threaded:
                self.ws_thread = threading.Thread(
                    target=self.ws.run_forever,
                    kwargs={"ping_interval": 30, "ping_timeout": 5}
                )
                self.ws_thread.daemon = True
                self.ws_thread.start()
            else:
                self.ws.run_forever(ping_interval=30, ping_timeout=5)
                
        except Exception as e:
            raise WebSocketError(f"Failed to connect: {str(e)}")
    
    def disconnect(self) -> None:
        """Disconnect WebSocket."""
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
    
    def _on_open(self, ws) -> None:
        """Handle WebSocket connection open."""
        self.is_connected = True
        logger.info("WebSocket connected")
        
        # Start heartbeat
        self._start_heartbeat()
        
        if self.on_connect:
            self.on_connect(ws)
    
    def _on_close(self, ws, close_status_code=None, close_msg=None) -> None:
        """Handle WebSocket connection close."""
        self.is_connected = False
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        if self.on_close:
            self.on_close(ws, close_status_code, close_msg)
    
    def _on_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
        
        if self.on_error:
            self.on_error(ws, error)
    
    def _on_message(self, ws, message) -> None:
        """Handle incoming WebSocket message."""
        try:
            if isinstance(message, bytes):
                # Binary tick data
                ticks = self._parse_binary_data(message)
                if ticks and self.on_tick:
                    self.on_tick(ws, ticks)
            else:
                # JSON message (usually acknowledgments)
                data = json.loads(message)
                logger.debug(f"Received JSON: {data}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _parse_binary_data(self, data: bytes) -> List[Dict[str, Any]]:
        """Parse binary tick data from Kite."""
        ticks = []
        
        try:
            # Binary packet structure (simplified)
            # Each packet: 2 bytes count + tick data
            offset = 0
            
            while offset < len(data):
                if len(data[offset:]) < 2:
                    break
                
                # Read packet count
                packet_count = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
                
                for _ in range(packet_count):
                    if offset >= len(data):
                        break
                    
                    # Parse tick based on mode (simplified version)
                    tick_size = 8  # Minimum LTP mode size
                    if len(data[offset:]) < tick_size:
                        break
                    
                    # Extract instrument token and LTP
                    instrument_token = struct.unpack('>I', data[offset:offset+4])[0]
                    last_price = struct.unpack('>I', data[offset+4:offset+8])[0] / 100.0
                    
                    tick = {
                        'instrument_token': instrument_token,
                        'last_price': last_price,
                        'timestamp': datetime.now()
                    }
                    
                    # Add more fields based on subscription mode
                    mode = self.token_modes.get(instrument_token, self.MODE_LTP)
                    
                    if mode in [self.MODE_QUOTE, self.MODE_FULL] and len(data[offset:]) >= 28:
                        # OHLC data
                        ohlc_offset = offset + 8
                        tick['ohlc'] = {
                            'open': struct.unpack('>I', data[ohlc_offset:ohlc_offset+4])[0] / 100.0,
                            'high': struct.unpack('>I', data[ohlc_offset+4:ohlc_offset+8])[0] / 100.0,
                            'low': struct.unpack('>I', data[ohlc_offset+8:ohlc_offset+12])[0] / 100.0,
                            'close': struct.unpack('>I', data[ohlc_offset+12:ohlc_offset+16])[0] / 100.0
                        }
                        
                        # Volume
                        volume = struct.unpack('>I', data[ohlc_offset+16:ohlc_offset+20])[0]
                        tick['volume'] = volume
                        
                        tick_size = 28
                    
                    if mode == self.MODE_FULL and len(data[offset:]) >= 44:
                        # Additional full mode data
                        # Average price, OI, etc.
                        tick_size = 44
                    
                    ticks.append(tick)
                    offset += tick_size
        
        except struct.error as e:
            logger.error(f"Binary parsing error: {e}")
        
        return ticks
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        def heartbeat():
            while not self._stop_event.is_set() and self.is_connected:
                time.sleep(30)  # Send heartbeat every 30 seconds
                if self.ws and self.is_connected:
                    try:
                        self.ws.ping()
                    except Exception as e:
                        logger.error(f"Heartbeat failed: {e}")
                        break
        
        self._heartbeat_thread = threading.Thread(target=heartbeat)
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()
    
    def subscribe(self, tokens: List[int], mode: str = MODE_LTP) -> None:
        """Subscribe to instrument tokens."""
        if not self.is_connected:
            raise WebSocketError("WebSocket not connected")
        
        # Store subscription info
        for token in tokens:
            self.subscribed_tokens.add(token)
            self.token_modes[token] = mode
        
        # Send subscription message
        message = {
            "a": "subscribe",
            "v": tokens
        }
        
        if mode != self.MODE_LTP:
            message["m"] = mode
        
        self._send_message(message)
    
    def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from instrument tokens."""
        if not self.is_connected:
            raise WebSocketError("WebSocket not connected")
        
        # Remove from tracking
        for token in tokens:
            self.subscribed_tokens.discard(token)
            self.token_modes.pop(token, None)
        
        # Send unsubscription message
        message = {
            "a": "unsubscribe",
            "v": tokens
        }
        
        self._send_message(message)
    
    def set_mode(self, tokens: List[int], mode: str) -> None:
        """Set mode for subscribed tokens."""
        if not self.is_connected:
            raise WebSocketError("WebSocket not connected")
        
        # Update mode tracking
        for token in tokens:
            if token in self.subscribed_tokens:
                self.token_modes[token] = mode
        
        # Send mode change message
        message = {
            "a": "mode",
            "v": tokens,
            "m": mode
        }
        
        self._send_message(message)
    
    def _send_message(self, message: Dict[str, Any]) -> None:
        """Send message to WebSocket."""
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(message))
            logger.debug(f"Sent message: {message}")
        else:
            raise WebSocketError("WebSocket not connected")
    
    def get_subscribed_tokens(self) -> List[int]:
        """Get list of currently subscribed tokens."""
        return list(self.subscribed_tokens)
    
    def is_token_subscribed(self, token: int) -> bool:
        """Check if token is subscribed."""
        return token in self.subscribed_tokens
