# `lib_zerodha` Design Document

**Version:** 2.0.0
**Architecture:** Modular Facade with Shared State
**Compliance:** Kite Connect API v3

---

   1. Architecture: Transformed a monolithic codebase into a clean Facade Pattern, delegating logic to specialized modules (auth, orders, market_data, portfolio, realtime).
   2. Compliance: Aligned data models (Quote, Order, Holding) with official Kite Connect v3 schemas and implemented forward-compatible parsing.
   3. Security: Implemented AES encryption for session tokens and atomic file locking to prevent corruption and unauthorized access.
   4. Stability: Fixed critical WebSocket bugs (binary parsing, reconnection) and standardized error handling.
   5. Features: Added support for GTT orders and Position Conversion, closing gaps with the official SDK.
   6. Quality: Achieved 100% pass rate on a comprehensive test suite (50 tests) covering all core workflows.
   7. Documentation: Produced detailed DESIGN.md, updated README.md, and maintained a clean project structure.

## 1. Executive Summary

`lib_zerodha` is a production-ready Python client for the Zerodha Kite Connect trading API. It is designed to be:
*   **Modular:** Features are encapsulated in specialized sub-packages (Auth, Orders, Market Data, etc.).
*   **Secure:** Sensitive data (session tokens) is encrypted at rest using industry-standard AES encryption with atomic persistence.
*   **Resilient:** Binary parsing for real-time data is robust against packet fragmentation and API changes.
*   **Idiomatic:** It uses Python type hinting, dataclasses, and standard exceptions throughout.

---

## 2. High-Level Architecture

The library implements the **Facade Design Pattern**.

### 2.1 The Facade (`KiteClient`)
*   **Location:** `lib_zerodha.kite_client.KiteClient`
*   **Role:** The single entry point for the user. It simplifies interaction by hiding the complexity of the subsystems.
*   **Responsibility:**
    *   Initializes the shared `requests.Session` and `KiteAuth` instance.
    *   Delegates specific tasks to specialized "Manager" classes (`KiteOrders`, `KiteMarketData`, etc.).
    *   Provides convenience methods that alias the delegated methods (e.g., `client.place_order` -> `client.orders.place_order`).

### 2.2 Shared State (`KiteAuth`)
*   **Location:** `lib_zerodha.auth.kite_auth.KiteAuth`
*   **Role:** The single source of truth for authentication state.
*   **Mechanism:**
    *   Maintains the `access_token`, `api_key`, and `user_profile`.
    *   Manages the HTTP `requests.Session` object with default headers (`X-Kite-Version: 3`, User-Agent).
    *   Shared instance ensures session state synchronization between `KiteClient` and `SessionManager`.

---

## 3. Module Breakdown

### 3.1 Authentication (`lib_zerodha.auth`)
*   **`KiteAuth`:** Handles the low-level HTTP session, login URL generation, and token validation.
*   **`SessionManager`:**
    *   **Secure Storage:** Uses `cryptography` (Fernet/AES) to encrypt session data before writing to disk.
    *   **Atomic Operations:** Uses `fcntl` file locking to prevent data corruption/race conditions during concurrent writes.
    *   **Auto-Refresh:** Can trigger a callback to fetch a new request token if the current session expires.

### 3.2 Orders (`lib_zerodha.orders`)
*   **`KiteOrders`:** Handles the full lifecycle of orders.
    *   **Standard Orders:** `place_order`, `modify_order`, `cancel_order`, `get_orders`, `get_trades`.
    *   **GTT (Good Till Triggered):** Full support for `place_gtt`, `modify_gtt`, `delete_gtt`, `get_gtts`, `get_gtt`.
*   **`OrderValidator`:** Pre-validates order parameters (quantity, product type, exchange) before sending the request to save API calls.
*   **`OrderType`, `ProductType`, etc.:** Enumerations for type safety.

### 3.3 Market Data (`lib_zerodha.market_data`)
*   **`KiteMarketData`:** Fetches Quote, LTP, OHLC, and Historical data.
*   **CSV Parsing:** Uses `pandas` and `io.StringIO` to efficiently parse the large instrument master CSV file returned by `get_instruments`.

### 3.4 Portfolio (`lib_zerodha.portfolio`)
*   **`KitePortfolio`:** Manages Positions and Holdings.
*   **Conversion:** `convert_position` allows converting between `MIS`, `CNC`, and `NRML` product types.
*   **Margins:** `get_margins` provides detailed equity and commodity margin utilization.

### 3.5 Real-time Data (`lib_zerodha.realtime`)
*   **`KiteWebSocket`:** A threaded WebSocket client.
*   **Binary Parsing:** Implements a robust binary parser for the Kite Ticker stream. It validates packet lengths and offsets dynamically to prevent crashes on malformed data.
*   **Reconnection:** Uses an exponential backoff strategy (non-blocking thread) to reconnect automatically upon network failure.

### 3.6 Models (`lib_zerodha.models`)
*   **Resilient Dataclasses:** All data models (`Quote`, `Order`, `Holding`, `Position`) use a `from_dict` factory method.
*   **Forward Compatibility:** The `from_dict` methods filter out unknown fields before initialization. This ensures the library doesn't crash if Zerodha adds new fields to the API response in the future.

---

## 4. Data Flow

### 4.1 Synchronous Request Flow (e.g., Place Order)
1.  **User Call:** `client.place_order(symbol="INFY", ...)`
2.  **Facade Delegation:** `KiteClient` calls `self.orders.place_order(...)`.
3.  **Validation:** `KiteOrders` uses `OrderValidator` to check inputs.
4.  **Auth Header:** `KiteOrders` calls `self.auth.get_auth_headers()` to get the current token.
5.  **HTTP Request:** `self.session.post(url, headers=headers, ...)` is sent.
6.  **Error Handling:** If the API returns 403, `ErrorHandler` raises `SessionExpiredError`.
7.  **Response:** JSON is parsed, and the `order_id` is returned to the user.

### 4.2 Real-time Tick Flow
1.  **Connection:** `client.websocket.connect()` spawns a background thread.
2.  **Stream:** Binary data arrives on the WebSocket.
3.  **Parsing:** `_on_message` calls `_parse_binary`, which slices the byte stream into individual packets.
4.  **Model Creation:** Each packet is converted into a `Tick` dataclass.
5.  **Callback:** The user's registered `on_tick` handler is called with the list of `Tick` objects.

---

## 5. Security Model

*   **Encryption:** `SessionManager` derives a 32-byte key from the `api_key` (or a custom password) using PBKDF2HMAC (SHA256, 100k iterations). This key encrypts the session file (`~/.lib_zerodha/session.enc`).
*   **Atomic Persistence:** Updates to the session file are atomic. A temporary file is written, flushed to disk (`fsync`), and then atomically renamed to the final filename. This prevents partial writes or file corruption during crashes.
*   **File Permissions:** The session directory is created with mode `700` (user-only access).
*   **Memory Hygiene:** `invalidate_session` overwrites the session file with random data before deletion to prevent forensic recovery.

---

## 6. Exception Hierarchy

All exceptions inherit from `LibZerodhaError`.

*   `LibZerodhaError`
    *   `AuthenticationError`
        *   `SessionExpiredError`
        *   `InvalidCredentialsError`
    *   `NetworkError`
    *   `APIError` (General API failures)
    *   `ValidationError`
    *   `OrderError`
    *   `MarketDataError`
    *   `WebSocketError`

This hierarchy allows users to catch specific errors (e.g., `except SessionExpiredError: re_login()`) or broad categories (`except NetworkError: retry()`).

---

## 7. Configuration

*   **`config.py`**: Centralized configuration management using environment variables (`LIB_ZERODHA_ENV`, `KITE_API_KEY`, etc.).
*   **Environments:** Supports `development`, `production`, and `sandbox` profiles with different base URLs.

---
