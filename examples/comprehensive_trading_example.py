"""Comprehensive examples for lib_zerodha trading system integration.

This file demonstrates all the enhanced features including:
- Complete Kite Connect API usage
- GTT (Good Till Triggered) orders
- Mutual Fund operations
- Position conversion
- Margin calculations
- Database storage integration
"""

import sys
import os
from datetime import datetime, date, timedelta
import pandas as pd

# Add lib_zerodha to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from lib_zerodha import (
    KiteClient, KiteWebSocketClient, DataProcessor, TradingDatabase,
    Quote, Order, Position, GTTTrigger, MFHolding
)


def comprehensive_trading_example():
    """Comprehensive example showing all trading system features."""
    
    # Initialize components
    api_key = "your_api_key"
    access_token = "your_access_token"
    
    # Initialize clients and database
    kite = KiteClient(api_key, access_token)
    db = TradingDatabase("trading_system.db")
    
    print("=== Kite Connect Trading System Integration ===\\n")
    
    # 1. Basic Market Data Operations
    print("1. Market Data Operations:")
    try:
        # Get quotes for multiple instruments
        instruments = [738561, 779521]  # Example: Reliance, HDFC Bank
        quotes = kite.get_quote(instruments)
        
        for token, quote_data in quotes.items():
            quote = Quote(
                instrument_token=int(token),
                timestamp=datetime.now(),
                last_price=quote_data['last_price'],
                volume=quote_data['volume'],
                average_price=quote_data.get('average_price', 0),
                ohlc=quote_data['ohlc']
            )
            
            # Store in database
            db.store_quote(quote)
            print(f"  {quote_data.get('instrument_token', token)}: ₹{quote.last_price}")
        
        print("  ✓ Market data stored in database\\n")
        
    except Exception as e:
        print(f"  ✗ Market data error: {e}\\n")
    
    # 2. Advanced Order Management
    print("2. Advanced Order Management:")
    try:
        # Place a complex bracket order
        order_id = kite.place_order(
            variety="bo",
            exchange="NSE", 
            tradingsymbol="SBIN",
            transaction_type="BUY",
            quantity=1,
            product="MIS",
            order_type="LIMIT",
            price=500.0,
            squareoff=5.0,  # 5 point profit target
            stoploss=2.0,   # 2 point stop loss
            tag="bracket_order_example"
        )
        print(f"  ✓ Bracket order placed: {order_id}")
        
        # Get and store order details
        orders = kite.get_orders()
        for order_data in orders:
            if order_data['order_id'] == order_id:
                order = Order(**order_data)
                db.store_order(order)
                print(f"  ✓ Order stored in database: {order.status}")
                break
        
    except Exception as e:
        print(f"  ✗ Order placement error: {e}")
    
    print()
    
    # 3. GTT (Good Till Triggered) Orders
    print("3. GTT Order Management:")
    try:
        # Place a two-leg GTT order
        trigger_id = kite.place_gtt(
            trigger_type="two-leg",
            tradingsymbol="SBIN",
            exchange="NSE",
            trigger_values=[480.0, 520.0],  # Trigger at 480 or 520
            last_price=500.0,
            orders=[
                {
                    "transaction_type": "SELL",
                    "quantity": 1,
                    "order_type": "MARKET",
                    "product": "CNC",
                    "price": 0
                }
            ]
        )
        print(f"  ✓ GTT order placed: {trigger_id}")
        
        # Get all GTT orders
        gtt_orders = kite.get_gtts()
        for gtt_data in gtt_orders:
            gtt = GTTTrigger(**gtt_data)
            db.store_gtt_trigger(gtt)
        
        print(f"  ✓ {len(gtt_orders)} GTT orders stored in database")
        
    except Exception as e:
        print(f"  ✗ GTT error: {e}")
    
    print()
    
    # 4. Mutual Fund Operations
    print("4. Mutual Fund Operations:")
    try:
        # Get MF instruments
        mf_instruments = kite.mf_instruments()
        print(f"  ✓ Retrieved {len(mf_instruments)} MF instruments")
        
        # Get MF holdings
        mf_holdings = kite.mf_holdings()
        if mf_holdings:
            mf_holding_objects = []
            for holding in mf_holdings:
                mf_holding = MFHolding(**holding)
                mf_holding_objects.append(mf_holding)
            
            db.store_mf_holdings(mf_holding_objects)
            print(f"  ✓ {len(mf_holdings)} MF holdings stored")
        else:
            print("  ℹ No MF holdings found")
        
        # Place MF SIP order (example)
        # sip_id = kite.place_mf_sip(
        #     tradingsymbol="INF109K01LX5",  # Example MF
        #     amount=1000.0,
        #     instalments=12,
        #     frequency="monthly",
        #     instalment_day=1
        # )
        # print(f"  ✓ MF SIP placed: {sip_id}")
        
    except Exception as e:
        print(f"  ✗ MF operations error: {e}")
    
    print()
    
    # 5. Position Management and Conversion
    print("5. Position Management:")
    try:
        # Get positions
        positions = kite.get_positions()
        
        if positions['day'] or positions['net']:
            # Convert position example (if positions exist)
            # result = kite.convert_position(
            #     exchange="NSE",
            #     tradingsymbol="SBIN",
            #     transaction_type="BUY",
            #     position_type="day",
            #     quantity=1,
            #     old_product="MIS",
            #     new_product="CNC"
            # )
            
            # Store positions in database
            all_positions = positions['day'] + positions['net']
            position_objects = [Position(**pos) for pos in all_positions]
            db.store_positions(position_objects)
            
            print(f"  ✓ {len(all_positions)} positions stored")
        else:
            print("  ℹ No positions found")
        
    except Exception as e:
        print(f"  ✗ Position management error: {e}")
    
    print()
    
    # 6. Margin Calculations
    print("6. Margin Calculations:")
    try:
        # Calculate order margins
        sample_orders = [
            {
                "exchange": "NSE",
                "tradingsymbol": "SBIN",
                "transaction_type": "BUY", 
                "variety": "regular",
                "product": "MIS",
                "order_type": "MARKET",
                "quantity": 1
            }
        ]
        
        margins = kite.order_margins(sample_orders)
        print(f"  ✓ Order margins calculated")
        print(f"    Required margin: ₹{margins[0].get('total', 0):.2f}")
        
        # Calculate basket margins
        basket_margins = kite.basket_order_margins(sample_orders)
        print(f"  ✓ Basket margins calculated")
        print(f"    Final margin required: ₹{basket_margins['final']['total']:.2f}")
        
    except Exception as e:
        print(f"  ✗ Margin calculation error: {e}")
    
    print()
    
    # 7. Historical Data and Technical Analysis
    print("7. Historical Data & Analysis:")
    try:
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        historical_data = kite.get_historical_data(
            instrument_token=738561,  # Reliance
            from_date=start_date,
            to_date=end_date,
            interval="day"
        )
        
        if not historical_data.data.empty:
            # Add technical indicators
            historical_data.add_technical_indicators()
            
            # Store in database
            db.store_historical_data(historical_data)
            
            print(f"  ✓ {len(historical_data.data)} days of historical data stored")
            print(f"    Latest close: ₹{historical_data.data['close'].iloc[-1]:.2f}")
            print(f"    20-day SMA: ₹{historical_data.data['sma_20'].iloc[-1]:.2f}")
            print(f"    RSI: {historical_data.data['rsi'].iloc[-1]:.2f}")
        
    except Exception as e:
        print(f"  ✗ Historical data error: {e}")
    
    print()
    
    # 8. Portfolio Analytics
    print("8. Portfolio Analytics:")
    try:
        # Calculate daily P&L
        daily_pnl = db.calculate_daily_pnl()
        print(f"  ✓ Daily P&L Summary:")
        print(f"    Total P&L: ₹{daily_pnl['total_pnl']:.2f}")
        print(f"    Realised P&L: ₹{daily_pnl['realised_pnl']:.2f}")
        print(f"    Unrealised P&L: ₹{daily_pnl['unrealised_pnl']:.2f}")
        
        # Get top gainers/losers
        gainers_losers = db.get_top_gainers_losers(5)
        
        if not gainers_losers['gainers'].empty:
            print("\\n    Top Gainers:")
            for _, stock in gainers_losers['gainers'].head(3).iterrows():
                print(f"      {stock['tradingsymbol']}: +{stock['day_change_percentage']:.2f}%")
        
        if not gainers_losers['losers'].empty:
            print("\\n    Top Losers:")
            for _, stock in gainers_losers['losers'].head(3).iterrows():
                print(f"      {stock['tradingsymbol']}: {stock['day_change_percentage']:.2f}%")
        
    except Exception as e:
        print(f"  ✗ Portfolio analytics error: {e}")
    
    print()
    
    # 9. Database Statistics and Maintenance
    print("9. Database Statistics:")
    try:
        stats = db.get_database_stats()
        print(f"  ✓ Database Statistics:")
        print(f"    Orders: {stats.get('orders_count', 0)}")
        print(f"    Trades: {stats.get('trades_count', 0)}")
        print(f"    Positions: {stats.get('positions_count', 0)}")
        print(f"    Quotes: {stats.get('quotes_count', 0)}")
        print(f"    Database Size: {stats.get('db_size_mb', 0):.2f} MB")
        
    except Exception as e:
        print(f"  ✗ Database statistics error: {e}")
    
    print("\\n=== Trading System Integration Complete ===")


def websocket_streaming_example():
    """Example of real-time data streaming with database storage."""
    
    print("\\n=== Real-time Data Streaming Example ===")
    
    api_key = "your_api_key"
    access_token = "your_access_token"
    
    db = TradingDatabase("streaming.db")
    processor = DataProcessor()
    
    # WebSocket event handlers
    def on_ticks(ws, ticks):
        """Handle incoming tick data."""
        for tick in ticks:
            # Convert to Quote object
            quote = Quote(
                instrument_token=tick['instrument_token'],
                timestamp=datetime.now(),
                last_price=tick['last_price'],
                volume=tick.get('volume_traded', 0),
                average_price=tick.get('average_traded_price', 0),
                ohlc=tick.get('ohlc', {})
            )
            
            # Store in database
            db.store_quote(quote)
            
            # Process with aggregator
            processor.add_quote(quote)
            
            print(f"Stored tick: {tick['instrument_token']} @ ₹{tick['last_price']}")
    
    def on_connect(ws, response):
        """Handle WebSocket connection."""
        print("Connected to WebSocket")
        # Subscribe to instruments
        instruments = [738561, 779521]  # Reliance, HDFC Bank
        ws.subscribe(instruments)
        ws.set_mode(ws.MODE_FULL, instruments)
    
    def on_error(ws, code, reason):
        """Handle WebSocket errors."""
        print(f"WebSocket error: {code} - {reason}")
    
    # Initialize WebSocket client
    ws = KiteWebSocketClient(api_key, access_token, debug=True)
    ws.on_ticks = on_ticks
    ws.on_connect = on_connect  
    ws.on_error = on_error
    
    print("Starting WebSocket connection...")
    print("Press Ctrl+C to stop")
    
    try:
        ws.connect(threaded=False)  # Blocking connection
    except KeyboardInterrupt:
        print("\\nStopping WebSocket connection...")
        ws.close()
        db.close()
        print("Stopped.")


def portfolio_analysis_example():
    """Example of portfolio analysis using stored data."""
    
    print("\\n=== Portfolio Analysis Example ===")
    
    db = TradingDatabase("trading_system.db")
    
    try:
        # Get recent quotes
        recent_quotes = db.get_quotes(
            start_time=datetime.now() - timedelta(hours=1)
        )
        print(f"Retrieved {len(recent_quotes)} recent quotes")
        
        # Get portfolio performance
        portfolio_history = db.get_portfolio_history(days=7)
        if not portfolio_history.empty:
            print("\\nWeekly Portfolio Performance:")
            for date in portfolio_history['date'].unique():
                day_data = portfolio_history[portfolio_history['date'] == date]
                equity_pnl = day_data[
                    (day_data['segment'] == 'equity') & 
                    (day_data['metric'] == 'total')
                ]['value'].sum()
                print(f"  {date}: ₹{equity_pnl:.2f}")
        
        # Get order analysis
        recent_orders = db.get_orders(start_date=datetime.now() - timedelta(days=1))
        if not recent_orders.empty:
            print(f"\\nLast 24 hours: {len(recent_orders)} orders")
            
            status_counts = recent_orders['status'].value_counts()
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
        
        # Get position summary  
        positions = db.get_positions()
        if not positions.empty:
            total_pnl = positions['pnl'].sum()
            print(f"\\nCurrent positions P&L: ₹{total_pnl:.2f}")
        
    except Exception as e:
        print(f"Analysis error: {e}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("Lib Zerodha - Comprehensive Trading System Integration\\n")
    print("Choose an example to run:")
    print("1. Comprehensive trading example")
    print("2. Real-time WebSocket streaming (requires valid API credentials)")
    print("3. Portfolio analysis from stored data")
    
    try:
        choice = input("\\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            comprehensive_trading_example()
        elif choice == "2":
            websocket_streaming_example()
        elif choice == "3":
            portfolio_analysis_example()
        else:
            print("Invalid choice. Running comprehensive example...")
            comprehensive_trading_example()
            
    except KeyboardInterrupt:
        print("\\nExample interrupted by user.")
    except Exception as e:
        print(f"\\nExample error: {e}")
        print("Make sure to set valid API credentials before running live examples.")