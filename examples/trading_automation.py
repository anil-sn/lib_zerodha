#!/usr/bin/env python3
"""Trading automation example with lib_zerodha."""

import os
from datetime import date, timedelta
from lib_zerodha import KiteClient
from lib_zerodha.exceptions import APIError

class TradingBot:
    """Simple trading bot example."""
    
    def __init__(self):
        self.kite = KiteClient(
            api_key=os.getenv("KITE_API_KEY"),
            access_token=os.getenv("KITE_ACCESS_TOKEN")
        )
        
        # Trading parameters
        self.watchlist = {
            "NSE:RELIANCE": 738561,
            "NSE:TCS": 408065,
            "NSE:INFY": 1270529
        }
        
        self.risk_params = {
            "max_position_size": 50000,  # Max ₹50K per position
            "stop_loss_pct": 2.0,        # 2% stop loss
            "target_pct": 4.0,           # 4% target
            "max_positions": 3           # Max 3 positions
        }
    
    def analyze_stock(self, symbol: str, token: int) -> dict:
        """Analyze stock for trading signals."""
        try:
            # Get historical data
            history = self.kite.historical_data(
                instrument_token=token,
                from_date=date.today() - timedelta(days=50),
                to_date=date.today(),
                interval="day"
            )
            
            if history.data.empty:
                return {"signal": "HOLD", "reason": "No data available"}
            
            # Add technical indicators
            history = history.add_technical_indicators()
            df = history.data
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # Simple strategy: RSI + SMA crossover
            signals = []
            reasons = []
            
            # RSI analysis
            if latest['rsi'] < 30:
                signals.append("BUY")
                reasons.append(f"RSI oversold ({latest['rsi']:.1f})")
            elif latest['rsi'] > 70:
                signals.append("SELL")
                reasons.append(f"RSI overbought ({latest['rsi']:.1f})")
            
            # SMA crossover
            if (latest['close'] > latest['sma_20'] and 
                prev['close'] <= prev['sma_20']):
                signals.append("BUY")
                reasons.append("Price crossed above SMA20")
            elif (latest['close'] < latest['sma_20'] and 
                  prev['close'] >= prev['sma_20']):
                signals.append("SELL")
                reasons.append("Price crossed below SMA20")
            
            # Volume confirmation
            avg_volume = df['volume'].tail(10).mean()
            if latest['volume'] > 1.5 * avg_volume:
                reasons.append("High volume confirmation")
            
            # Determine final signal
            buy_signals = signals.count("BUY")
            sell_signals = signals.count("SELL")
            
            if buy_signals > sell_signals:
                final_signal = "BUY"
            elif sell_signals > buy_signals:
                final_signal = "SELL"
            else:
                final_signal = "HOLD"
            
            return {
                "signal": final_signal,
                "reasons": reasons,
                "current_price": latest['close'],
                "rsi": latest['rsi'],
                "sma_20": latest['sma_20'],
                "volume_ratio": latest['volume'] / avg_volume
            }
        
        except Exception as e:
            return {"signal": "HOLD", "reason": f"Analysis error: {e}"}
    
    def check_existing_positions(self) -> dict:
        """Check existing positions for the watchlist stocks."""
        try:
            positions = self.kite.positions()
            existing = {}
            
            for position in positions:
                if position.quantity != 0:  # Active position
                    symbol = f"{position.exchange}:{position.tradingsymbol}"
                    existing[symbol] = {
                        "quantity": position.quantity,
                        "avg_price": position.average_price,
                        "ltp": position.last_price,
                        "pnl": position.pnl,
                        "product": position.product
                    }
            
            return existing
        
        except Exception as e:
            print(f"Error checking positions: {e}")
            return {}
    
    def calculate_position_size(self, price: float) -> int:
        """Calculate position size based on risk parameters."""
        max_shares = int(self.risk_params["max_position_size"] / price)
        return min(max_shares, 100)  # Cap at 100 shares for example
    
    def place_trade_order(self, symbol: str, signal: str, price: float, analysis: dict) -> bool:
        """Place a trading order based on signal."""
        try:
            exchange, tradingsymbol = symbol.split(":")
            quantity = self.calculate_position_size(price)
            
            if quantity == 0:
                print(f"⚠️  Position size too small for {symbol} at ₹{price}")
                return False
            
            # Calculate prices
            if signal == "BUY":
                order_price = price * 1.001  # Slightly above LTP
                stop_loss = price * (1 - self.risk_params["stop_loss_pct"] / 100)
                target = price * (1 + self.risk_params["target_pct"] / 100)
            else:  # SELL
                order_price = price * 0.999  # Slightly below LTP
                stop_loss = price * (1 + self.risk_params["stop_loss_pct"] / 100)
                target = price * (1 - self.risk_params["target_pct"] / 100)
            
            # Place main order
            order_id = self.kite.place_order(
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=signal,
                quantity=quantity,
                product="MIS",  # Intraday
                order_type="LIMIT",
                price=round(order_price, 2),
                tag="lib_zerodha_bot"
            )
            
            print(f"✅ {signal} order placed for {symbol}:")
            print(f"   Order ID: {order_id}")
            print(f"   Quantity: {quantity}")
            print(f"   Price: ₹{order_price:.2f}")
            print(f"   Stop Loss: ₹{stop_loss:.2f}")
            print(f"   Target: ₹{target:.2f}")
            print(f"   Reasons: {', '.join(analysis['reasons'])}")
            
            return True
        
        except APIError as e:
            print(f"❌ Order placement failed for {symbol}: {e}")
            return False
    
    def manage_existing_positions(self, existing_positions: dict):
        """Manage existing positions (stop loss, targets)."""
        for symbol, position in existing_positions.items():
            current_pnl_pct = (position['pnl'] / (position['avg_price'] * abs(position['quantity']))) * 100
            
            print(f"\n📊 Managing position: {symbol}")
            print(f"   Quantity: {position['quantity']}")
            print(f"   Avg Price: ₹{position['avg_price']:.2f}")
            print(f"   LTP: ₹{position['ltp']:.2f}")
            print(f"   P&L: ₹{position['pnl']:.2f} ({current_pnl_pct:+.2f}%)")
            
            # Check stop loss
            if current_pnl_pct <= -self.risk_params["stop_loss_pct"]:
                print(f"   ⚠️  Stop loss triggered! Current loss: {current_pnl_pct:.2f}%")
                # In real trading, you would place a market order to exit
            
            # Check target
            elif current_pnl_pct >= self.risk_params["target_pct"]:
                print(f"   🎯 Target achieved! Current profit: {current_pnl_pct:.2f}%")
                # In real trading, you would place a market order to book profits
            
            else:
                print(f"   ✅ Position within normal range")
    
    def run_strategy(self):
        """Run the complete trading strategy."""
        print("🤖 Starting trading bot...")
        print(f"Watchlist: {list(self.watchlist.keys())}")
        print(f"Risk Parameters: {self.risk_params}")
        print("="*60)
        
        try:
            # Check existing positions
            existing_positions = self.check_existing_positions()
            active_positions = len(existing_positions)
            
            print(f"\n📈 Current active positions: {active_positions}")
            
            if existing_positions:
                self.manage_existing_positions(existing_positions)
            
            # Analyze watchlist stocks
            print(f"\n🔍 Analyzing watchlist stocks...")
            
            for symbol, token in self.watchlist.items():
                if active_positions >= self.risk_params["max_positions"]:
                    print(f"⚠️  Maximum positions ({self.risk_params['max_positions']}) reached")
                    break
                
                if symbol in existing_positions:
                    print(f"⏩ Skipping {symbol} - already in position")
                    continue
                
                print(f"\n📊 Analyzing {symbol}...")
                
                # Get current quote
                quotes = self.kite.quote([symbol])
                if symbol not in quotes:
                    print(f"❌ Could not get quote for {symbol}")
                    continue
                
                current_price = quotes[symbol].last_price
                print(f"   Current Price: ₹{current_price:.2f}")
                
                # Analyze for signals
                analysis = self.analyze_stock(symbol, token)
                
                print(f"   Signal: {analysis['signal']}")
                if 'reasons' in analysis:
                    print(f"   Reasons: {', '.join(analysis['reasons'])}")
                if 'rsi' in analysis:
                    print(f"   RSI: {analysis['rsi']:.1f}")
                if 'volume_ratio' in analysis:
                    print(f"   Volume Ratio: {analysis['volume_ratio']:.1f}x")
                
                # Execute trade if signal is strong
                if analysis['signal'] in ["BUY", "SELL"] and 'reasons' in analysis:
                    if len(analysis['reasons']) >= 2:  # Require at least 2 confirming signals
                        success = self.place_trade_order(symbol, analysis['signal'], current_price, analysis)
                        if success:
                            active_positions += 1
                    else:
                        print(f"   ⚠️  Signal not strong enough (only {len(analysis['reasons'])} confirmations)")
        
        except Exception as e:
            print(f"❌ Strategy execution error: {e}")
        
        print("\n✅ Trading bot execution completed.")

def main():
    """Main function."""
    # Check environment variables
    if not os.getenv("KITE_API_KEY") or not os.getenv("KITE_ACCESS_TOKEN"):
        print("❌ Please set KITE_API_KEY and KITE_ACCESS_TOKEN environment variables")
        return
    
    print("⚠️  WARNING: This is a demo trading bot for educational purposes only!")
    print("⚠️  Always test thoroughly before using real money.")
    print("⚠️  The authors are not responsible for any trading losses.\n")
    
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        return
    
    # Run the bot
    bot = TradingBot()
    bot.run_strategy()

if __name__ == "__main__":
    main()
