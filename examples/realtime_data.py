#!/usr/bin/env python3
"""Real-time data streaming example with lib_zerodha."""

import os
import time
import signal
import sys
from threading import Event
from lib_zerodha import KiteWebSocket, DataProcessor
from lib_zerodha.exceptions import WebSocketError

class RealTimeDataExample:
    """Real-time data streaming example."""
    
    def __init__(self):
        self.processor = DataProcessor(max_candles_per_interval=500)
        self.stop_event = Event()
        self.ws = None
        
        # Stock tokens (example)
        self.tokens = {
            738561: "RELIANCE",
            408065: "TCS", 
            1270529: "ICICIBANK",
            2714625: "SBIN",
            81153: "HDFCBANK"
        }
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\nShutting down gracefully...")
        self.stop_event.set()
        if self.ws:
            self.ws.disconnect()
        sys.exit(0)
    
    def on_connect(self):
        """WebSocket connection callback."""
        print("✅ WebSocket connected!")
        
        # Subscribe to tokens
        tokens_list = list(self.tokens.keys())
        print(f"Subscribing to {len(tokens_list)} instruments...")
        
        # Subscribe with different modes
        self.ws.subscribe(tokens_list[:3], mode="full")  # Full data for first 3
        self.ws.subscribe(tokens_list[3:], mode="quote")  # Quote data for rest
        
        print("Subscription complete. Waiting for ticks...")
    
    def on_tick(self, ticks):
        """Process incoming ticks."""
        for tick in ticks:
            # Process tick through data processor
            self.processor.process_tick(tick)
            
            token = tick.instrument_token
            symbol = self.tokens.get(token, str(token))
            ltp = tick.last_price
            
            # Print live updates (throttled)
            if int(time.time()) % 5 == 0:  # Every 5 seconds
                print(f"{symbol}: ₹{ltp:,.2f}", end=" | ")
    
    def on_error(self, error):
        """Handle WebSocket errors."""
        print(f"❌ WebSocket error: {error}")
    
    def on_close(self, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"\n🔌 WebSocket disconnected: {close_status_code}")
    
    def print_stats(self):
        """Print periodic statistics."""
        while not self.stop_event.is_set():
            time.sleep(10)  # Every 10 seconds
            
            if self.stop_event.is_set():
                break
                
            print("\n" + "="*60)
            print("📊 LIVE MARKET STATISTICS")
            print("="*60)
            
            # Processor stats
            stats = self.processor.get_stats()
            print(f"Instruments tracked: {stats['instruments_tracked']}")
            print(f"Cached quotes: {stats['cached_quotes']}")
            
            # Latest quotes
            print("\n🔥 Latest Quotes:")
            for token, symbol in self.tokens.items():
                quote = self.processor.get_latest_quote(token)
                if quote:
                    change_pct = ((quote.last_price - quote.ohlc.close) / quote.ohlc.close) * 100
                    print(f"  {symbol:<12}: ₹{quote.last_price:>8.2f} ({change_pct:+.2f}%)")
            
            # Candle data
            print("\n📈 5-Minute Candles (Last 3):")
            for token, symbol in list(self.tokens.items())[:3]:
                candles = self.processor.get_candles(token, "5minute", count=3)
                if candles:
                    latest = candles[-1]
                    print(f"  {symbol}: O:{latest.open:.2f} H:{latest.high:.2f} L:{latest.low:.2f} C:{latest.close:.2f} V:{latest.volume}")
            
            # Interval statistics
            print("\n📊 Interval Statistics:")
            for interval, interval_stats in stats['intervals'].items():
                if interval_stats['total_candles'] > 0:
                    print(f"  {interval:<10}: {interval_stats['total_candles']} candles, {interval_stats['current_building']} building")
    
    def run(self):
        """Run the real-time data example."""
        try:
            print("🚀 Starting real-time data streaming...")
            
            # Initialize WebSocket client
            self.ws = KiteWebSocket(
                api_key=os.getenv("KITE_API_KEY"),
                access_token=os.getenv("KITE_ACCESS_TOKEN")
            )
            
            # Register handlers
            self.ws.on_connect(self.on_connect)
            self.ws.on_tick(self.on_tick)
            self.ws.on_error(self.on_error)
            self.ws.on_close(self.on_close)
            
            # Connect WebSocket
            self.ws.connect(threaded=True)
            
            # Start statistics thread
            import threading
            stats_thread = threading.Thread(target=self.print_stats)
            stats_thread.daemon = True
            stats_thread.start()
            
            print("\n📡 Connected! Press Ctrl+C to stop.")
            print("💡 Tip: Watch the live updates and statistics below.\n")
            
            # Keep running until stopped
            while not self.stop_event.is_set():
                time.sleep(1)
        
        except WebSocketError as e:
            print(f"WebSocket error: {e}")
        
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        finally:
            print("\n📈 Final Statistics:")
            final_stats = self.processor.get_stats()
            print(f"Total instruments processed: {final_stats['instruments_tracked']}")
            
            # Export data summary
            export_data = self.processor.export_to_dict()
            total_candles = sum(
                len(candles) 
                for interval_data in export_data['candles'].values() 
                for candles in interval_data.values()
            )
            print(f"Total candles generated: {total_candles}")
            print("\n✅ Shutdown complete.")

def main():
    """Main function."""
    # Check environment variables
    if not os.getenv("KITE_API_KEY") or not os.getenv("KITE_ACCESS_TOKEN"):
        print("❌ Please set KITE_API_KEY and KITE_ACCESS_TOKEN environment variables")
        return
    
    # Run example
    example = RealTimeDataExample()
    example.run()

if __name__ == "__main__":
    main()