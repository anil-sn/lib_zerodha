#!/usr/bin/env python3
"""Basic usage examples for lib_zerodha."""

import os
from datetime import date, timedelta
from lib_zerodha import KiteClient
from lib_zerodha.exceptions import APIError, AuthenticationError

def main():
    """Demonstrate basic lib_zerodha usage."""
    
    # Initialize client
    kite = KiteClient(
        api_key=os.getenv("KITE_API_KEY"),
        access_token=os.getenv("KITE_ACCESS_TOKEN")
    )
    
    try:
        # 1. Get user profile
        print("=== User Profile ===")
        profile = kite.profile()
        print(f"Name: {profile['user_name']}")
        print(f"Email: {profile['email']}")
        print(f"Broker: {profile['broker']}")
        
        # 2. Get margins
        print("\n=== Account Margins ===")
        margins = kite.margins()
        print(f"Total Available: ₹{margins.total_available:,.2f}")
        
        # 3. Get market quotes
        print("\n=== Market Quotes ===")
        instruments = ["NSE:RELIANCE", "NSE:TCS", "NSE:INFY"]
        quotes = kite.quote(instruments)
        
        for symbol, quote in quotes.items():
            print(f"{symbol}:")
            print(f"  LTP: ₹{quote.last_price:,.2f}")
            print(f"  Change: {((quote.last_price - quote.ohlc.close) / quote.ohlc.close) * 100:+.2f}%")
            print(f"  Volume: {quote.volume:,}")
        
        # 4. Get historical data
        print("\n=== Historical Data ===")
        history = kite.historical_data(
            instrument_token=738561,  # RELIANCE
            from_date=date.today() - timedelta(days=30),
            to_date=date.today(),
            interval="day"
        )
        
        print(f"Retrieved {len(history.data)} days of data")
        print("Last 5 days:")
        print(history.data.tail())
        
        # Add technical indicators
        history_with_indicators = history.add_technical_indicators()
        print("\nWith technical indicators:")
        print(history_with_indicators.data[['close', 'sma_20', 'sma_50', 'rsi']].tail())
        
        # 5. Portfolio overview
        print("\n=== Portfolio Overview ===")
        portfolio = kite.get_portfolio()
        
        if portfolio.positions:
            print(f"Active Positions: {len(portfolio.positions)}")
            print(f"Total P&L: ₹{portfolio.total_pnl:,.2f}")
            
            positions_df = portfolio.to_dataframe("positions")
            profitable = positions_df[positions_df['pnl'] > 0]
            print(f"Profitable positions: {len(profitable)}/{len(positions_df)}")
        
        if portfolio.holdings:
            print(f"Long-term Holdings: {len(portfolio.holdings)}")
            holdings_df = portfolio.to_dataframe("holdings")
            total_investment = holdings_df['average_price'].sum()
            current_value = holdings_df['last_price'].sum()
            print(f"Holdings P&L: ₹{current_value - total_investment:,.2f}")
        
        # 6. Recent orders and trades
        print("\n=== Recent Orders ===")
        orders = kite.orders()
        if orders:
            print(f"Orders today: {len(orders)}")
            for order in orders[-3:]:  # Last 3 orders
                print(f"  {order.tradingsymbol} {order.transaction_type} {order.quantity} @ ₹{order.price} - {order.status}")
        else:
            print("No orders today")
        
        trades = kite.trades()
        if trades:
            print(f"\nTrades today: {len(trades)}")
            for trade in trades[-3:]:  # Last 3 trades
                print(f"  {trade.tradingsymbol} {trade.transaction_type} {trade.quantity} @ ₹{trade.average_price}")
        else:
            print("No trades today")
    
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Please check your API key and access token")
    
    except APIError as e:
        print(f"API Error: {e}")
        if e.error_code:
            print(f"Error Code: {e.error_code}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
