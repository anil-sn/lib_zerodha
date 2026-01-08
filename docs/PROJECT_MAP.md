# Project Map: lib_zerodha

## 📂 Root Directory
*   `README.md` - Project overview and usage guide.
*   `requirements.txt` - Project dependencies.
*   `setup.py` - Installation script.
*   `pytest.ini` - Test configuration.

## 📚 Documentation (`docs/`)
*   `DESIGN.md` - Comprehensive architectural design document.
*   `BRUTAL_CODE_REVIEW.md` - Audit log of the v2.0 refactoring.
*   `PROJECT_MAP.md` - This file.

## 🧩 Source Code (`lib_zerodha/`)
*   `kite_client.py` - **The Facade.** Main entry point for the library.
*   `__init__.py` - Package initialization and exports.

### Sub-Modules
*   `auth/` - Authentication & Session Management.
    *   `kite_auth.py` - Low-level auth logic.
    *   `session_manager.py` - Encryption & persistence.
*   `orders/` - Order Management.
    *   `kite_orders.py` - Order placement & modification.
    *   `order_validation.py` - Pre-flight validation logic.
*   `market_data/` - Market Data.
    *   `kite_market_data.py` - Quotes, OHLC, Historical data.
*   `portfolio/` - Portfolio Management.
    *   `kite_portfolio.py` - Positions & Holdings.
*   `realtime/` - WebSocket.
    *   `kite_websocket.py` - Threaded WebSocket client.
*   `models/` - Data Models.
    *   `base.py` - Core models (Quote, Order).
    *   `portfolio.py` - Portfolio models (Position, Holding).
    *   `market_data.py` - Real-time models (Tick).
*   `exceptions/` - Error Handling.
    *   `api_exceptions.py` - Exception hierarchy.
*   `config/` - Configuration.
    *   `base_config.py`, `development.py`, etc.

## 🧪 Tests (`tests/`)
*   `conftest.py` - Shared fixtures & Mock Server.
*   `integration/` - End-to-end workflow tests.
*   `test_auth/` - Authentication unit tests.
*   `test_client/` - Facade client unit tests.
*   `test_market_data/` - Market data unit tests.
*   `test_orders/` - Order management unit tests.
*   `test_portfolio/` - Portfolio unit tests.