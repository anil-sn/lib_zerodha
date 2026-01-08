# lib_zerodha

A production-ready, modular, and secure Python client for the Zerodha Kite Connect API (v3).

## 🌟 Features

*   **Modular Architecture:** Clean separation of concerns (Auth, Orders, Market Data, Portfolio).
*   **Secure Session Management:** AES-256 encryption for session tokens at rest.
*   **Type Safety:** Fully type-hinted using Python `dataclasses` and `typing`.
*   **Resilient:** Robust error handling and forward-compatible data models.
*   **Real-time Ready:** High-performance threaded WebSocket client with automatic reconnection.
*   **Full API Coverage:** Supports Orders, GTT, Portfolio, Market Data, and Historical Data.

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

### 1. Authentication & Session Management

```python
from lib_zerodha import KiteClient

# Initialize client
client = KiteClient(api_key="your_api_key", api_secret="your_api_secret")

# Generate session (first time login)
# You get the 'request_token' from the Kite Connect redirect URL
client.generate_session(request_token="request_token_from_url")

# The session is now encrypted and saved to ~/.lib_zerodha/session.enc
# Future runs will automatically load the session if it's valid.
```

### 2. Market Data

```python
# Fetch live quotes
quotes = client.get_quote(["NSE:INFY", "NSE:RELIANCE"])
print(f"INFY LTP: {quotes['NSE:INFY'].last_price}")

# Fetch instrument master
instruments = client.get_instruments(exchange="NSE")
print(instruments.head())
```

### 3. Order Placement

```python
order_id = client.place_order(
    variety="regular",
    exchange="NSE",
    tradingsymbol="INFY",
    transaction_type="BUY",
    quantity=1,
    product="CNC",
    order_type="MARKET"
)
print(f"Order placed: {order_id}")
```

### 4. WebSocket Streaming

```python
def on_tick(ticks):
    for tick in ticks:
        print(f"Tick: {tick.instrument_token} -> {tick.last_price}")

ws = client.websocket
ws.on_tick(on_tick)
ws.connect()

ws.subscribe([408065, 738561]) # Subscribe to tokens
```

## 🏗️ Architecture

See [docs/DESIGN.md](docs/DESIGN.md) for a detailed architectural overview.

## 🧪 Testing

Run the full test suite:

```bash
pytest
```

## 🔒 Security Note

Session tokens are stored in `~/.lib_zerodha/session.enc` encrypted with a key derived from your API Key. Ensure your machine is secure.

## 📄 License

MIT License