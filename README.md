# lib_zerodha: Comprehensive Kite Connect Trading System

A complete, production-ready Python library for Zerodha's Kite Connect API with advanced features for trading systems, database storage, and portfolio management.

## 🚀 Key Features

### Complete API Coverage
- **All Kite Connect v3 APIs** - Orders, Positions, Holdings, Market Data
- **GTT Orders** - Good Till Triggered orders with single and two-leg support
- **Mutual Funds** - Complete MF orders, SIPs, and holdings management
- **Position Conversion** - Convert positions between product types
- **Advanced Margins** - Order margins, basket margins, and charges calculation
- **Auction Instruments** - Support for auction session trading

### Database Integration
- **High-Performance Storage** - SQLite with WAL mode for concurrent access
- **Complete Data Models** - Optimized pandas-ready data structures
- **Portfolio Analytics** - Built-in P&L tracking and performance analysis
- **Historical Data** - Efficient storage and retrieval with technical indicators
- **Real-time Storage** - WebSocket data automatically stored

### Advanced Features
- **WebSocket Streaming** - Real-time market data with automatic reconnection
- **Technical Analysis** - Built-in indicators (SMA, RSI, Volume analysis)
- **Data Processing** - Optimized aggregation and transformation
- **Error Handling** - Comprehensive exception handling with retry logic
- **Concurrency** - Thread-safe operations with connection pooling

## 📦 Installation

### Using uv (Recommended)

```bash
# Basic installation
uv add lib_zerodha

# With analysis tools (numpy, pandas, ta-lib)
uv add "lib_zerodha[analysis]"

# With database support (SQLite optimizations)
uv add "lib_zerodha[database]"

# With performance optimizations (ujson, orjson)
uv add "lib_zerodha[performance]"

# Development installation (all dependencies)
uv add "lib_zerodha[dev]"

# All optional dependencies
uv add "lib_zerodha[all]"
```

### Using pip

```bash
# Basic installation
pip install lib_zerodha

# With optional dependencies
pip install "lib_zerodha[analysis,database,performance]"
```

### Local Development

```bash
# Clone and install for development
git clone <repository-url>
cd lib_zerodha

# Using uv (recommended)
uv sync
uv run python -m pytest  # Run tests

# Or using pip
pip install -e ".[dev]"
python -m pytest
```

## 🔧 Quick Start

### Basic Setup
```python
from lib_zerodha import KiteClient, TradingDatabase

# Initialize client
kite = KiteClient("your_api_key", "your_access_token")

# Initialize database
db = TradingDatabase("trading.db")

# Get market data and store
quotes = kite.get_quote([738561])  # Reliance
for token, quote_data in quotes.items():
    # Automatically converts to optimized data structures
    quote = Quote(instrument_token=int(token), **quote_data)
    db.store_quote(quote)
```

### Advanced Order Management
```python
# Place bracket order with stop-loss and target
order_id = kite.place_order(
    variety="bo",
    exchange="NSE",
    tradingsymbol="SBIN", 
    transaction_type="BUY",
    quantity=1,
    product="MIS",
    order_type="LIMIT",
    price=500.0,
    squareoff=5.0,  # ₹5 profit target
    stoploss=2.0    # ₹2 stop loss
)

# Place GTT (Good Till Triggered) order
gtt_id = kite.place_gtt(
    trigger_type="two-leg",
    tradingsymbol="SBIN",
    exchange="NSE", 
    trigger_values=[480.0, 520.0],
    last_price=500.0,
    orders=[{
        "transaction_type": "SELL",
        "quantity": 1,
        "order_type": "MARKET",
        "product": "CNC",
        "price": 0
    }]
)
```

### Mutual Fund Operations
```python
# Place MF order
mf_order_id = kite.place_mf_order(
    tradingsymbol="INF109K01LX5",
    transaction_type="BUY",
    amount=1000.0
)

# Start SIP
sip_id = kite.place_mf_sip(
    tradingsymbol="INF109K01LX5",
    amount=1000.0,
    instalments=12,
    frequency="monthly",
    instalment_day=1
)

# Get MF holdings with automatic database storage
mf_holdings = kite.mf_holdings()
mf_objects = [MFHolding(**holding) for holding in mf_holdings]
db.store_mf_holdings(mf_objects)
```

### Position Management
```python
# Get positions
positions = kite.get_positions()

# Convert position from MIS to CNC
kite.convert_position(
    exchange="NSE",
    tradingsymbol="SBIN",
    transaction_type="BUY", 
    position_type="day",
    quantity=1,
    old_product="MIS",
    new_product="CNC"
)

# Store positions with analytics
all_positions = positions['day'] + positions['net'] 
position_objects = [Position(**pos) for pos in all_positions]
db.store_positions(position_objects)

# Get daily P&L
daily_pnl = db.calculate_daily_pnl()
print(f"Today's P&L: ₹{daily_pnl['total_pnl']:.2f}")
```

### Margin Calculations
```python
# Calculate order margins
orders = [{
    "exchange": "NSE",
    "tradingsymbol": "SBIN",
    "transaction_type": "BUY",
    "variety": "regular", 
    "product": "MIS",
    "order_type": "MARKET",
    "quantity": 1
}]

# Individual order margins
margins = kite.order_margins(orders)
print(f"Required margin: ₹{margins[0]['total']:.2f}")

# Basket margins (with netting benefits)
basket_margins = kite.basket_order_margins(orders)
print(f"Final margin: ₹{basket_margins['final']['total']:.2f}")

# Calculate charges
charges = kite.get_virtual_contract_note(orders)
```

### Real-time Data Streaming
```python
from lib_zerodha import KiteWebSocketClient, DataProcessor

# Setup WebSocket with automatic database storage
ws = KiteWebSocketClient("api_key", "access_token")
processor = DataProcessor()
db = TradingDatabase("streaming.db")

def on_ticks(ws, ticks):
    for tick in ticks:
        quote = Quote(
            instrument_token=tick['instrument_token'],
            timestamp=datetime.now(),
            last_price=tick['last_price'],
            volume=tick.get('volume_traded', 0)
        )
        
        # Store in database
        db.store_quote(quote)
        
        # Process for analytics
        processor.add_quote(quote)

ws.on_ticks = on_ticks
ws.connect()
```

### Portfolio Analytics
```python
# Get portfolio performance
portfolio_history = db.get_portfolio_history(days=30)

# Top gainers and losers  
gainers_losers = db.get_top_gainers_losers(10)
print("Top Gainers:")
for _, stock in gainers_losers['gainers'].iterrows():
    print(f"{stock['tradingsymbol']}: +{stock['day_change_percentage']:.2f}%")

# Historical data with technical indicators
historical = kite.get_historical_data(
    instrument_token=738561,
    from_date=datetime.now() - timedelta(days=100),
    to_date=datetime.now(),
    interval="day"
)

# Add technical indicators
historical.add_technical_indicators()
print(f"Current RSI: {historical.data['rsi'].iloc[-1]:.2f}")

# Store historical data
db.store_historical_data(historical)
```

## 🏗️ Architecture

### Data Models
All API responses are converted to optimized pandas-ready data classes:

```python
@dataclass
class Quote:
    instrument_token: int
    timestamp: datetime
    last_price: float
    ohlc: OHLC
    volume: int = 0
    depth: Dict[str, List[DepthItem]] = field(default_factory=dict)
    
    def to_pandas(self) -> pd.Series:
        # Optimized pandas conversion
```

### Database Schema
Comprehensive database design for trading systems:

- **quotes** - Real-time market data with millisecond timestamps
- **historical_data** - OHLC data with multiple timeframes  
- **orders** - Complete order lifecycle tracking
- **trades** - Trade execution details
- **positions** - Daily position snapshots with P&L
- **holdings** - Long-term holdings with performance metrics
- **gtt_triggers** - GTT order management
- **mf_holdings** - Mutual fund portfolio
- **portfolio_snapshots** - Daily portfolio analytics

### Performance Features
- **Connection Pooling** - Efficient database access
- **WAL Mode** - Concurrent read/write operations
- **Indexed Queries** - Optimized for trading system queries
- **Batch Operations** - Bulk data processing
- **Automatic Cleanup** - Configurable data retention

## 📊 API Coverage

### Market Data APIs ✅
- `get_quote()` - Real-time quotes
- `get_ohlc()` - OHLC data  
- `get_ltp()` - Last traded price
- `get_historical_data()` - Historical candles
- `get_instruments()` - Instrument master
- `mf_instruments()` - Mutual fund instruments

### Order Management APIs ✅  
- `place_order()` - All order types (Regular, BO, CO, AMO)
- `modify_order()` - Order modifications
- `cancel_order()` - Order cancellation
- `get_orders()` - Order history
- `get_order_history()` - Order updates
- `get_trades()` - Trade book
- `order_trades()` - Order-specific trades

### Portfolio APIs ✅
- `get_positions()` - Live positions
- `convert_position()` - Product conversion
- `get_holdings()` - Long-term holdings
- `get_auction_instruments()` - Auction instruments

### GTT APIs ✅
- `place_gtt()` - Good Till Triggered orders
- `get_gtts()` - GTT order list
- `get_gtt()` - Individual GTT details
- `modify_gtt()` - GTT modifications  
- `delete_gtt()` - GTT cancellation

### Mutual Fund APIs ✅
- `mf_orders()` - MF order history
- `place_mf_order()` - Place MF orders
- `cancel_mf_order()` - Cancel MF orders
- `mf_sips()` - SIP details
- `place_mf_sip()` - Start SIP
- `modify_mf_sip()` - Modify SIP
- `cancel_mf_sip()` - Stop SIP
- `mf_holdings()` - MF portfolio

### Margin & Analytics APIs ✅
- `order_margins()` - Order margin requirements
- `basket_order_margins()` - Basket margins with netting
- `get_virtual_contract_note()` - Charges calculation
- `trigger_range()` - Cover order trigger range
- `market_margins()` - Segment-wise margins

### Session APIs ✅
- `generate_session()` - Login and token generation
- `renew_access_token()` - Token renewal
- `invalidate_refresh_token()` - Logout

## 🔒 Security & Best Practices

```python
# Secure credential management
import os
from lib_zerodha import KiteClient

kite = KiteClient(
    api_key=os.getenv("KITE_API_KEY"),
    access_token=os.getenv("KITE_ACCESS_TOKEN")
)

# Connection pooling for high-frequency trading
db = TradingDatabase("trading.db", pool_size=10)

# Error handling with retries
try:
    order_id = kite.place_order(...)
except RateLimitError:
    time.sleep(1)  # Rate limit backoff
    order_id = kite.place_order(...)
```

## 📈 Examples

See [comprehensive_trading_example.py](examples/comprehensive_trading_example.py) for:

1. **Complete Trading Workflow** - Orders, GTT, positions, margins
2. **Real-time Data Processing** - WebSocket streaming with storage
3. **Portfolio Analytics** - Performance tracking and analysis
4. **Database Operations** - Efficient data storage and retrieval
5. **Risk Management** - Position sizing and P&L monitoring

## 🛠️ Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Database maintenance
python -c "
from lib_zerodha import TradingDatabase
db = TradingDatabase('trading.db')
print(db.get_database_stats())
db.cleanup_old_data(days=30)
"
```

## 📝 License

MIT License - Built on top of the official Kite Connect API