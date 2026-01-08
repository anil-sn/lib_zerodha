# Project Map: lib_zerodha

## 📂 Root Directory
*   `README.md`: Project overview and usage guide.
*   `requirements.txt`: Project dependencies.
*   `setup.py`: Installation script.
*   `pytest.ini`: Test configuration.
*   `Makefile`: Build and test automation.

## 📚 Documentation (`docs/`)
*   `DESIGN.md`: Comprehensive architectural design document.
*   `REVIEW.md`: Audit log of the v2.0 refactoring and current issues.
*   `PROJECT_MAP.md`: This file.
*   `TODO.md`: Task tracking.

## 🧩 Source Code (`lib_zerodha/`)
*   `__init__.py`: Package initialization.
*   `kite_client.py`: **Facade Client**.
    *   `KiteClient`: Main class integrating Auth, Orders, Market Data, Portfolio, and Realtime.

### 🔐 Authentication (`lib_zerodha/auth/`)
*   `kite_auth.py`:
    *   `KiteAuth`: Handles login URL generation, token exchange (`generate_session`), and session validation.
*   `session_manager.py`:
    *   `SessionManager`: Manages secure session storage (encrypted file), auto-refresh, and atomic file operations.

### 📈 Market Data (`lib_zerodha/market_data/`)
*   `kite_market_data.py`:
    *   `KiteMarketData`: Fetches Quote, LTP, OHLC, Historical Data, and Instruments list.

### 🛒 Orders (`lib_zerodha/orders/`)
*   `kite_orders.py`:
    *   `KiteOrders`: Handles `place_order`, `modify_order`, `cancel_order`, `get_orders`, `get_trades`, and GTT operations.
*   `order_types.py`: Enums for `OrderType`, `ProductType`, `TransactionType`, `Variety`.
*   `order_validation.py`: `OrderValidator` for pre-flight check of order parameters.

### 💼 Portfolio (`lib_zerodha/portfolio/`)
*   `kite_portfolio.py`:
    *   `KitePortfolio`: Fetches `get_positions`, `get_holdings`, `get_margins`, and handles `convert_position`.

### ⚡ Realtime (`lib_zerodha/realtime/`)
*   `kite_websocket.py`: **Primary WebSocket Implementation**.
    *   `KiteWebSocket`: Robust client with reconnection logic and binary parsing.
*   `subscriptions.py`:
    *   `SubscriptionManager`: Manages groups of subscriptions and data processing.
*   `candle_store.py`: **[DEPRECATED]** In-memory candle aggregation (use `utils.DataProcessor` instead).
*   `data_handlers.py`: (Assumed) handlers for different data types.
*   `websocket_manager.py`: (Assumed) higher-level manager.

### 📊 Derivatives (`lib_zerodha/derivatives/`)
*   `kite_fo.py`:
    *   `KiteFO`: F&O specific operations, option chain fetching (`get_option_chain`), and Greeks calculation.
*   `expiry_utils.py`: Utilities for calculating expiry dates.
*   `option_chain.py`: Analysis logic for option chains.

### 📦 Models (`lib_zerodha/models/`)
*   `base.py`:
    *   `Quote`, `OHLC`, `DepthItem`: Market data models.
    *   `Order`, `Trade`: Order execution models.
    *   `Position`, `Holding`, `Portfolio`: Portfolio models.
    *   `Instrument`: Instrument master model.
*   `derivatives.py`:
    *   `OptionChain`, `FOInstrument`: F&O specific models.
*   `market_data.py`: (Likely imports from base or specific market data models).
*   `portfolio.py`: (Likely imports from base or specific portfolio models).

### ⚙️ Configuration (`lib_zerodha/config/`)
*   `base_config.py`:
    *   `Config`: Base configuration class loading from env vars.
*   `development.py`: Dev profile.
*   `production.py`: Prod profile.

### 💾 Storage (`lib_zerodha/storage/`)
*   `base_storage.py`: Abstract base class for storage.
*   `memory_storage.py`: In-memory storage implementation.
*   `sqlite_storage.py`: SQLite storage implementation.

### 🛠️ Utilities (`lib_zerodha/utils/`)
*   `error_handler.py`:
    *   `ErrorHandler`: Centralized exception handling and mapping.
*   `data_processor.py`: Utilities for data processing.
*   `date_utils.py`: Date manipulation helpers.

### ⚠️ Exceptions (`lib_zerodha/exceptions/`)
*   `api_exceptions.py`: Custom exception hierarchy (`LibZerodhaError`, `NetworkError`, `APIError`, etc.).

## 🧪 Tests (`tests/`)
*   `conftest.py`: Pytest fixtures and mock server setup.
*   `test_client/`: Tests for `KiteClient`.
*   `test_auth/`: Tests for `KiteAuth` and `SessionManager`.
*   `test_orders/`: Tests for order placement and validation.
*   `test_market_data/`: Tests for quotes and historical data.
*   `integration/`: End-to-end integration tests.
