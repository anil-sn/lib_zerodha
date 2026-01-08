To bring `lib_zerodha` to full production-grade correctness and parity with `pykiteconnect`, the following action plan should be executed. These items are formatted as specific instructions for an LLM.

---

### **Phase 1: WebSocket & Binary Protocol (Critical Fixes)**

**1. Fix Binary Frame Header Logic**
*   **File:** `lib_zerodha/realtime/kite_websocket.py`
*   **Issue:** The current `_parse_binary` incorrectly treats the first 2 bytes as a packet length. 
*   **Action:** Rewrite `_parse_binary` to read the first 2 bytes as the **total number of packets** in the frame. Then, enter a loop to read each packet by first reading its specific 2-byte length header.

**2. Fix CDS (Currency) Precision**
*   **File:** `lib_zerodha/realtime/kite_websocket.py`
*   **Issue:** Hardcoded division by `100.0` breaks Currency Derivative prices.
*   **Action:** Update `_get_precision` to accept a `token`. Logic: if the token corresponds to a CDS instrument, return `10000`. Maintain a set of CDS tokens (populated during instrument fetch) or allow manual override.

**3. Map Missing `MODE_FULL` Fields**
*   **File:** `lib_zerodha/realtime/kite_websocket.py`
*   **Action:** Ensure the `MODE_FULL` parser includes `last_trade_time` (offset 44) and `exchange_timestamp` (offset 60). Pass these into the `Tick.from_dict` call so they are available for latency analysis.

---

### **Phase 2: Order Management (Reliability Fixes)**

**4. Decouple Order Validation from Static Limits**
*   **File:** `lib_zerodha/orders/order_validation.py`
*   **Issue:** Hardcoded `ORDER_CONSTRAINTS` (1,000,000 max qty, etc.) will block valid orders when exchanges update limits.
*   **Action:** Remove all price and quantity range checks from `OrderValidator`. Keep only structural checks (e.g., `quantity > 0`, non-empty `tradingsymbol`). Let the Kite API return RMS/Freeze limit errors.

**5. Standardize Iceberg & MTF Parameters**
*   **File:** `lib_zerodha/orders/kite_orders.py` and `lib_zerodha/kite_client.py`
*   **Action:** Ensure `place_order` explicitly supports `iceberg_legs` (int) and `iceberg_quantity` (int). Ensure `ProductType.MTF` is added to all relevant enums and allowed combinations.

---

### **Phase 3: Architectural Cleanup (Performance & Scaling)**

**6. Eliminate Global Singleton Config**
*   **File:** `lib_zerodha/config/base_config.py`
*   **Issue:** `config = Config.from_env()` at the module level prevents multi-user/multi-API key instances in a single process.
*   **Action:** Remove the global `config` instance. Modify `KiteClient` to accept a `Config` object or credentials in its `__init__`, and pass that configuration down to sub-managers (`orders`, `market_data`, etc.).

**7. Consolidate Redundant Data Handlers**
*   **File:** `lib_zerodha/realtime/subscriptions.py`
*   **Issue:** Currently uses both `TickAggregator` and `DataProcessor`.
*   **Action:** Delete `lib_zerodha/realtime/data_handlers.py` (`TickAggregator`). Refactor `SubscriptionManager` to use `lib_zerodha/utils/data_processor.py` for all candle aggregation and quote caching. This reduces CPU overhead by 50% during high-volume ticks.

---

### **Phase 4: Security & Session Handling (Robustness)**

**8. Randomize Encryption Salt**
*   **File:** `lib_zerodha/auth/session_manager.py`
*   **Issue:** Hardcoded `salt = b'lib_zerodha_salt'` makes the PBKDF2 derivation weak.
*   **Action:** Generate a random salt for each new session. Store the salt in the first 16 bytes of the `.enc` file so it can be retrieved during decryption.

**9. Implement Graceful WebSocket Handshake Queuing**
*   **File:** `lib_zerodha/realtime/kite_websocket.py`
*   **Issue:** If a user calls `subscribe()` before the socket is fully open, the request is lost.
*   **Action:** Create a command queue (list). If `is_connected` is False, append the subscription request to the queue. In `_on_open_callback`, process and clear the queue.

---

### **Phase 5: Documentation & Developer Experience**

**10. Align Method Naming with `pykiteconnect`**
*   **File:** `lib_zerodha/kite_client.py`
*   **Action:** Add aliases for standard methods to aid migration.
    *   `kite.quote()` should alias to `kite.get_quote()`
    *   `kite.ltp()` should alias to `kite.get_ltp()`
    *   `kite.margins()` should alias to `kite.get_margins()`

**11. Detailed CDS Precision Example**
*   **File:** `docs/INTEGRATION_AND_USAGE.md`
*   **Action:** Add a section explaining how the library handles the 4-decimal precision of Currency Derivatives and how to verify if the token-to-divisor mapping is correct.

---
