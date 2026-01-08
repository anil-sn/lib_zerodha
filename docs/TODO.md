# TODO List

## ✅ Completed Tasks (v2.0 Refactor)

- [x] **Modular Architecture:** Split monolithic client into `auth`, `orders`, `market_data`, `portfolio`, `realtime`.
- [x] **Secure Sessions:** Implemented AES encryption for session tokens.
- [x] **Data Model Compliance:** Aligned `Quote`, `Order`, `Holding` models with Kite Connect v3.
- [x] **Facade Implementation:** Created clean `KiteClient` facade.
- [x] **Test Coverage:** Achieved 100% pass rate (47/47 tests) with comprehensive unit and integration tests.
- [x] **Documentation:** Created `DESIGN.md` and updated `README.md`.
- [x] **GTT Support:** Implement `place_gtt`, `modify_gtt`, `delete_gtt` for Good Till Triggered orders.
- [x] **Real-time Hardening:** Robust binary parsing and reconnection logic for WebSocket.
- [x] **WebSocket Unification:** Merged `KiteWebSocket` and `KiteWebSocketClient` into a single robust implementation. Fixed subscription manager compatibility.
- [x] **Mutual Funds:** Added support for Mutual Fund orders and SIPs (`mf_*` methods) via `KiteMF` and `KiteClient.mf`.

## 🚀 Future Enhancements (Post-Release)

- [ ] **AsyncIO Support:** Introduce an asynchronous client (`AsyncKiteClient`) using `aiohttp`.
- [ ] **Advanced Analytics:** Add built-in technical indicators (RSI, MACD) to `HistoricalData`.
- [ ] **Backtesting Engine:** Create a simple event-driven backtester using the historical data module.
- [ ] **Docker Support:** Add `Dockerfile` and `docker-compose.yml` for containerized deployment.
