# Integration and Usage Guide

This guide provides a comprehensive overview of how to integrate and use `lib_zerodha` in your trading applications.

## 1. Installation

Install `lib_zerodha` using pip (assuming it's packaged or installed from source):

```bash
pip install lib_zerodha
```

Or install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 2. Configuration

`lib_zerodha` uses a centralized configuration system but primarily relies on passing API credentials during initialization or setting them via environment variables.

**Environment Variables:**
*   `KITE_API_KEY`: Your Kite Connect API Key.
*   `KITE_ACCESS_TOKEN`: Your valid Access Token (obtained after login flow).
*   `KITE_API_SECRET`: (Optional) Your API Secret, needed for generating a new session.

## 3. Core Usage

The primary entry point is the `KiteClient` class.

### 3.1 Authentication

**Option A: Using an existing Access Token**

If you already have a valid access token (e.g., manually generated or stored), you can initialize the client directly.

```python
import os
from lib_zerodha import KiteClient

kite = KiteClient(
    api_key="your_api_key",
    access_token="your_access_token"
)

# Verify session
if kite.is_authenticated():
    print("Logged in successfully!")
```

**Option B: Full Login Flow (Generating Session)**

If you need to generate an access token from a request token (redirected from Zerodha's login page):

1.  Generate the login URL for the user.
2.  User logs in and is redirected with a `request_token`.
3.  Exchange `request_token` for an `access_token`.

```python
from lib_zerodha import KiteClient

# 1. Initialize with API Key and Secret
kite = KiteClient(api_key="your_api_key", api_secret="your_api_secret")

# 2. Get login URL
login_url = kite.get_login_url()
print(f"Login here: {login_url}")

# ... User logs in ...
request_token = "token_from_url_redirect"

# 3. Generate Session
session_data = kite.generate_session(request_token)
print(f"Access Token: {session_data['access_token']}")
```

### 3.2 Market Data

Fetch real-time quotes, LTP, or OHLC data.

```python
# Get full quotes
instruments = ["NSE:INFY", "NSE:RELIANCE"]
quotes = kite.get_quote(instruments)

for symbol, quote in quotes.items():
    print(f"{symbol} LTP: {quote.last_price}")
    print(f"Volume: {quote.volume}")

# Get LTP only (lighter request)
ltp = kite.get_ltp(instruments)
print(f"INFY LTP: {ltp['NSE:INFY']}")
```

### 3.3 Historical Data

Retrieve historical candle data for analysis or backtesting.

```python
from datetime import date, timedelta

# Fetch daily candles for the last 30 days
history = kite.get_historical_data(
    instrument_token=738561,  # RELIANCE
    from_date=date.today() - timedelta(days=30),
    to_date=date.today(),
    interval="day"
)

# Access as Pandas DataFrame
print(history.data.head())

# Add technical indicators (SMA, RSI, etc.)
history.add_technical_indicators()
print(history.data[['close', 'sma_20', 'rsi']].tail())
```

### 3.4 Order Management

Place, modify, and cancel orders.

```python
from lib_zerodha.orders import OrderType, TransactionType, ProductType

# Place a Limit Order
try:
    order_id = kite.place_order(
        tradingsymbol="INFY",
        exchange="NSE",
        transaction_type=TransactionType.BUY,
        quantity=1,
        order_type=OrderType.LIMIT,
        product=ProductType.CNC,
        price=1400.0,
        tag="my_strategy"
    )
    print(f"Order Placed: {order_id}")

    # Modify the order
    kite.modify_order(
        order_id=order_id,
        price=1405.0
    )
    
    # Cancel the order
    kite.cancel_order(order_id)

except Exception as e:
    print(f"Order failed: {e}")
```

### 3.5 Portfolio

Manage positions and holdings.

```python
# Get positions
positions = kite.get_positions()
for pos in positions['net']:
    print(f"{pos.tradingsymbol}: P&L {pos.pnl}")

# Get holdings
holdings = kite.get_holdings()
for holding in holdings:
    print(f"{holding.tradingsymbol}: Qty {holding.quantity}")
```

## 4. Real-time Integration (WebSocket)

`lib_zerodha` provides a robust, threaded WebSocket client for streaming market data.

### 4.1 Basic Setup

```python
from lib_zerodha import KiteWebSocket

def on_tick(ticks):
    for tick in ticks:
        print(f"Token: {tick.instrument_token} LTP: {tick.last_price}")

def on_connect():
    print("Connected to WebSocket")
    # Subscribe to tokens
    ws.subscribe([738561, 408065], mode="full")

# Initialize
ws = KiteWebSocket(
    api_key="your_api_key",
    access_token="your_access_token"
)

# Register callbacks
ws.on_tick(on_tick)
ws.on_connect(on_connect)

# Start connection (blocking=False runs in background thread)
ws.connect(threaded=True)

# Keep main thread alive
import time
while True:
    time.sleep(1)
```

### 4.2 Using DataProcessor

The `DataProcessor` utility simplifies handling real-time streams by automatically aggregating ticks into candles (1min, 5min, etc.) and maintaining a cache of the latest quotes.

```python
from lib_zerodha import KiteWebSocket, DataProcessor

# Initialize processor
processor = DataProcessor(max_candles_per_interval=1000)

def on_tick(ticks):
    for tick in ticks:
        # Feed tick to processor
        processor.process_tick(tick)
        
        # Get real-time stats
        latest_quote = processor.get_latest_quote(tick.instrument_token)
        print(f"LTP: {latest_quote.last_price}")

# ... Setup WebSocket as above ...
```

### 4.3 Handling Currency Derivatives (CDS)

Currency Derivatives (CDS) on Kite have a precision of 4 decimal places (division by 10000.0), unlike Equity/NFO which use 2 decimal places (division by 100.0).

To ensure correct prices for CDS instruments, you must explicitly set the precision divisor using `set_precision`.

```python
# Setup for USDINR (CDS)
usdinr_token = 123456  # Example token

# Configure precision map BEFORE subscribing
ws.set_precision(usdinr_token, 10000)

# Subscribe
ws.subscribe([usdinr_token], mode="full")

# Ticks will now report correct LTP (e.g., 83.4500 instead of 8345.00)
```

## 5. F&O / Derivatives

Specialized support for Futures and Options.

```python
# Get Option Chain
option_chain = kite.derivatives.get_option_chain(
    symbol="NIFTY",
    expiry="2024-01-25",
    exchange="NFO"
)

# Analyze chain
atm_strike = option_chain.get_atm_strike()
print(f"ATM Strike: {atm_strike}")

# Get DataFrame
df = option_chain.to_dataframe()
print(df.head())
```

## 6. Error Handling

The library uses a hierarchy of exceptions for robust error handling.

```python
from lib_zerodha.exceptions import (
    TokenException,      # Auth/Token issues
    NetworkError,        # Connection issues
    OrderError,          # Order placement failures
    InputException       # Invalid parameters
)

try:
    kite.place_order(...)
except TokenException:
    print("Session expired. Please re-login.")
except InputException as e:
    print(f"Invalid input: {e}")
except NetworkError:
    print("Network failed. Retrying...")
except Exception as e:
    print(f"Unknown error: {e}")
```
