"""Subscription management for real-time data."""

from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime
import threading

from ..models.market_data import Tick
from .kite_websocket import KiteWebSocket
from .data_handlers import TickAggregator, MarketDepthProcessor, RealTimeQuoteManager


class SubscriptionManager:
    """Manages WebSocket subscriptions and data processing."""
    
    def __init__(self, websocket: KiteWebSocket):
        """Initialize subscription manager.
        
        Args:
            websocket: WebSocket client
        """
        self.websocket = websocket
        
        # Subscription tracking
        self._subscriptions = {}  # instrument_token -> subscription_info
        self._subscription_groups = {}  # group_name -> Set[instrument_token]
        self._lock = threading.RLock()
        
        # Data processors
        self.tick_aggregator = TickAggregator()
        self.depth_processor = MarketDepthProcessor()
        self.quote_manager = RealTimeQuoteManager()
        
        # Register WebSocket handlers
        self.websocket.on_tick(self._handle_ticks)
        self.websocket.on_connect(self._on_websocket_connect)
        self.websocket.on_close(self._on_websocket_close)
        self.websocket.on_error(self._on_websocket_error)
        
        # Status tracking
        self._is_connected = False
        self._last_tick_time = None
        
        # Event callbacks
        self._on_tick_callbacks = []
        self._on_quote_callbacks = []
        self._on_status_callbacks = []
    
    def _handle_ticks(self, ticks: List[Tick]):
        """Handle incoming ticks from WebSocket."""
        self._last_tick_time = datetime.now()
        
        for tick in ticks:
            # Process through data handlers
            self.tick_aggregator.process_tick(tick)
            self.depth_processor.process_tick(tick)
            self.quote_manager.process_tick(tick)
            
            # Notify tick callbacks
            for callback in self._on_tick_callbacks:
                try:
                    callback(tick)
                except Exception:
                    pass
    
    def _on_websocket_connect(self):
        """Handle WebSocket connection."""
        self._is_connected = True
        self._notify_status_change('connected')
    
    def _on_websocket_close(self, code, reason):
        """Handle WebSocket disconnection."""
        self._is_connected = False
        self._notify_status_change('disconnected', {'code': code, 'reason': reason})
    
    def _on_websocket_error(self, error: Exception):
        """Handle WebSocket error."""
        self._notify_status_change('error', {'error': str(error)})
    
    def _notify_status_change(self, status: str, data: Optional[Dict[str, Any]] = None):
        """Notify status change callbacks."""
        status_data = {
            'status': status,
            'timestamp': datetime.now(),
            'data': data or {}
        }
        
        for callback in self._on_status_callbacks:
            try:
                callback(status_data)
            except Exception:
                pass
    
    # Subscription management
    def subscribe(self, instrument_tokens: List[int], 
                 mode: str = KiteWebSocket.MODE_LTP,
                 group_name: Optional[str] = None) -> None:
        """Subscribe to instruments.
        
        Args:
            instrument_tokens: List of instrument tokens
            mode: Subscription mode (ltp, quote, full)
            group_name: Optional group name for batch management
        """
        if not instrument_tokens:
            return
        
        with self._lock:
            # Track subscriptions
            subscription_info = {
                'mode': mode,
                'subscribed_at': datetime.now(),
                'group_name': group_name
            }
            
            for token in instrument_tokens:
                self._subscriptions[token] = subscription_info
            
            # Track groups
            if group_name:
                if group_name not in self._subscription_groups:
                    self._subscription_groups[group_name] = set()
                self._subscription_groups[group_name].update(instrument_tokens)
        
        # Subscribe through WebSocket
        self.websocket.subscribe(instrument_tokens, mode)
    
    def unsubscribe(self, instrument_tokens: Optional[List[int]] = None,
                   group_name: Optional[str] = None) -> None:
        """Unsubscribe from instruments.
        
        Args:
            instrument_tokens: Specific tokens to unsubscribe (optional)
            group_name: Group name to unsubscribe (optional)
        """
        tokens_to_unsubscribe = []
        
        with self._lock:
            if group_name and group_name in self._subscription_groups:
                # Unsubscribe entire group
                tokens_to_unsubscribe = list(self._subscription_groups[group_name])
                del self._subscription_groups[group_name]
                
                # Remove from individual subscriptions
                for token in tokens_to_unsubscribe:
                    self._subscriptions.pop(token, None)
            
            elif instrument_tokens:
                # Unsubscribe specific tokens
                tokens_to_unsubscribe = instrument_tokens
                
                for token in instrument_tokens:
                    # Remove from subscriptions
                    sub_info = self._subscriptions.pop(token, None)
                    
                    # Remove from groups
                    if sub_info and sub_info.get('group_name'):
                        group = self._subscription_groups.get(sub_info['group_name'])
                        if group:
                            group.discard(token)
                            if not group:
                                del self._subscription_groups[sub_info['group_name']]
        
        if tokens_to_unsubscribe:
            self.websocket.unsubscribe(tokens_to_unsubscribe)
    
    def unsubscribe_all(self):
        """Unsubscribe from all instruments."""
        with self._lock:
            all_tokens = list(self._subscriptions.keys())
            self._subscriptions.clear()
            self._subscription_groups.clear()
        
        if all_tokens:
            self.websocket.unsubscribe(all_tokens)
    
    def change_mode(self, instrument_tokens: List[int], mode: str):
        """Change subscription mode for instruments."""
        with self._lock:
            for token in instrument_tokens:
                if token in self._subscriptions:
                    self._subscriptions[token]['mode'] = mode
        
        self.websocket.set_mode(instrument_tokens, mode)
    
    # Subscription info
    def get_subscribed_instruments(self) -> Dict[int, Dict[str, Any]]:
        """Get all subscribed instruments with their info."""
        with self._lock:
            return self._subscriptions.copy()
    
    def get_subscription_groups(self) -> Dict[str, Set[int]]:
        """Get all subscription groups."""
        with self._lock:
            return {name: group.copy() for name, group in self._subscription_groups.items()}
    
    def is_subscribed(self, instrument_token: int) -> bool:
        """Check if instrument is subscribed."""
        return instrument_token in self._subscriptions
    
    def get_subscription_count(self) -> int:
        """Get total number of subscriptions."""
        return len(self._subscriptions)
    
    # Status and health
    def get_status(self) -> Dict[str, Any]:
        """Get subscription manager status."""
        return {
            'connected': self._is_connected,
            'websocket_connected': self.websocket.is_connected,
            'subscription_count': len(self._subscriptions),
            'group_count': len(self._subscription_groups),
            'last_tick_time': self._last_tick_time,
            'uptime_seconds': (
                (datetime.now() - self._subscriptions[list(self._subscriptions.keys())[0]]['subscribed_at']).total_seconds()
                if self._subscriptions else 0
            )
        }
    
    def is_healthy(self) -> bool:
        """Check if subscription manager is healthy."""
        if not self._is_connected or not self.websocket.is_connected:
            return False
        
        # Check if we're receiving ticks (if subscribed)
        if self._subscriptions and self._last_tick_time:
            seconds_since_last_tick = (datetime.now() - self._last_tick_time).total_seconds()
            return seconds_since_last_tick < 60  # Should receive ticks within 60 seconds
        
        return True
    
    # Event handlers
    def on_tick(self, callback: Callable[[Tick], None]):
        """Register tick event handler."""
        self._on_tick_callbacks.append(callback)
    
    def on_quote_update(self, callback: Callable[[Dict[str, Any]], None]):
        """Register quote update handler."""
        self.quote_manager.on_quote_update(callback)
    
    def on_status_change(self, callback: Callable[[Dict[str, Any]], None]):
        """Register status change handler."""
        self._on_status_callbacks.append(callback)
    
    # Convenience methods
    def subscribe_symbols(self, symbols: List[str], exchange: str = "NSE",
                         mode: str = KiteWebSocket.MODE_LTP) -> Dict[str, int]:
        """Subscribe to instruments by symbol names.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
            mode: Subscription mode
            
        Returns:
            Dictionary mapping symbols to instrument tokens
        """
        # This would require instrument lookup functionality
        # For now, return empty dict - implement with instruments database
        return {}
    
    def create_watchlist(self, name: str, symbols: List[str], 
                        exchange: str = "NSE",
                        mode: str = KiteWebSocket.MODE_QUOTE) -> bool:
        """Create and subscribe to a watchlist.
        
        Args:
            name: Watchlist name
            symbols: List of symbols
            exchange: Exchange name
            mode: Subscription mode
            
        Returns:
            True if successful
        """
        try:
            # Convert symbols to tokens (implementation needed)
            token_map = self.subscribe_symbols(symbols, exchange, mode)
            
            if token_map:
                tokens = list(token_map.values())
                self.subscribe(tokens, mode, group_name=f"watchlist_{name}")
                return True
        except Exception:
            pass
        
        return False
    
    def get_watchlist_data(self, name: str) -> Dict[str, Any]:
        """Get real-time data for a watchlist.
        
        Args:
            name: Watchlist name
            
        Returns:
            Dictionary with watchlist data
        """
        group_name = f"watchlist_{name}"
        
        if group_name in self._subscription_groups:
            tokens = list(self._subscription_groups[group_name])
            quotes = self.quote_manager.get_quotes(tokens)
            
            return {
                'name': name,
                'tokens': tokens,
                'quotes': quotes,
                'count': len(tokens),
                'active_count': len(quotes)
            }
        
        return {'name': name, 'error': 'Watchlist not found'}