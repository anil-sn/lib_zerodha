"""Database storage module for trading system integration.

Provides efficient storage and retrieval of trading data with support for
multiple database backends and optimized queries for trading systems.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import threading
from contextlib import contextmanager

from .data_models import (
    Quote, Order, Position, Holding, Trade, 
    GTTTrigger, MFHolding, HistoricalData, MarginInfo
)
from .exceptions import DatabaseError


class TradingDatabase:
    """High-performance database for trading system data storage."""
    
    def __init__(self, db_path: str = "trading.db", pool_size: int = 5):
        """Initialize trading database.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Connection pool size for concurrent access
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self._local = threading.local()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Market data tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    instrument_token INTEGER,
                    timestamp DATETIME,
                    last_price REAL,
                    volume INTEGER,
                    average_price REAL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    depth_data TEXT,
                    PRIMARY KEY (instrument_token, timestamp)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quotes_timestamp 
                ON quotes(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quotes_instrument
                ON quotes(instrument_token)
            """)
            
            # Historical data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS historical_data (
                    instrument_token INTEGER,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    timeframe TEXT DEFAULT 'day',
                    PRIMARY KEY (instrument_token, date, timeframe)
                )
            """)
            
            # Orders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    exchange_order_id TEXT,
                    parent_order_id TEXT,
                    tradingsymbol TEXT,
                    exchange TEXT,
                    instrument_token INTEGER,
                    transaction_type TEXT,
                    variety TEXT,
                    product TEXT,
                    order_type TEXT,
                    quantity INTEGER,
                    price REAL,
                    trigger_price REAL,
                    average_price REAL,
                    pending_quantity INTEGER,
                    filled_quantity INTEGER,
                    cancelled_quantity INTEGER,
                    disclosed_quantity INTEGER,
                    validity TEXT,
                    validity_ttl INTEGER,
                    status TEXT,
                    status_message TEXT,
                    order_timestamp DATETIME,
                    exchange_timestamp DATETIME,
                    exchange_update_timestamp DATETIME,
                    placed_by TEXT,
                    tag TEXT,
                    guid TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_timestamp 
                ON orders(order_timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status
                ON orders(status)
            """)
            
            # Trades table  
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    order_id TEXT,
                    exchange TEXT,
                    tradingsymbol TEXT,
                    instrument_token INTEGER,
                    transaction_type TEXT,
                    product TEXT,
                    average_price REAL,
                    quantity INTEGER,
                    exchange_timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                )
            """)
            
            # Positions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    tradingsymbol TEXT,
                    exchange TEXT,
                    instrument_token INTEGER,
                    product TEXT,
                    quantity INTEGER,
                    overnight_quantity INTEGER,
                    multiplier REAL,
                    average_price REAL,
                    close_price REAL,
                    last_price REAL,
                    value REAL,
                    pnl REAL,
                    m2m REAL,
                    unrealised REAL,
                    realised REAL,
                    buy_quantity INTEGER,
                    buy_price REAL,
                    buy_value REAL,
                    buy_m2m REAL,
                    sell_quantity INTEGER,
                    sell_price REAL,
                    sell_value REAL,
                    sell_m2m REAL,
                    day_buy_quantity INTEGER,
                    day_buy_price REAL,
                    day_buy_value REAL,
                    day_sell_quantity INTEGER,
                    day_sell_price REAL,
                    day_sell_value REAL,
                    date DATE DEFAULT (DATE('now')),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tradingsymbol, exchange, product, date)
                )
            """)
            
            # Holdings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    tradingsymbol TEXT,
                    exchange TEXT,
                    instrument_token INTEGER,
                    isin TEXT,
                    product TEXT,
                    price REAL,
                    quantity INTEGER,
                    used_quantity INTEGER,
                    t1_quantity INTEGER,
                    realised_quantity INTEGER,
                    authorised_quantity INTEGER,
                    authorised_date DATE,
                    opening_quantity INTEGER,
                    collateral_quantity INTEGER,
                    collateral_type TEXT,
                    discrepancy BOOLEAN,
                    average_price REAL,
                    last_price REAL,
                    close_price REAL,
                    pnl REAL,
                    day_change REAL,
                    day_change_percentage REAL,
                    date DATE DEFAULT (DATE('now')),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tradingsymbol, exchange, date)
                )
            """)
            
            # GTT triggers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gtt_triggers (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    type TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    expires_at DATETIME,
                    status TEXT,
                    condition TEXT,
                    orders TEXT,
                    local_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Mutual Fund holdings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mf_holdings (
                    folio TEXT,
                    fund TEXT,
                    tradingsymbol TEXT,
                    average_price REAL,
                    last_price REAL,
                    last_price_date DATE,
                    pnl REAL,
                    quantity REAL,
                    date DATE DEFAULT (DATE('now')),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (folio, tradingsymbol, date)
                )
            """)
            
            # Portfolio snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    date DATE,
                    segment TEXT,
                    metric TEXT,
                    value REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, segment, metric)
                )
            """)
            
            # Market data statistics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_stats (
                    date DATE,
                    instrument_token INTEGER,
                    tradingsymbol TEXT,
                    high REAL,
                    low REAL,
                    volume INTEGER,
                    turnover REAL,
                    vwap REAL,
                    PRIMARY KEY (date, instrument_token)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with connection pooling."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path, 
                timeout=30.0,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        
        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
    
    # Market Data Storage Methods
    def store_quote(self, quote: Quote):
        """Store real-time quote data."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO quotes (
                    instrument_token, timestamp, last_price, volume, 
                    average_price, open, high, low, close, depth_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quote.instrument_token,
                quote.timestamp,
                quote.last_price,
                quote.volume,
                quote.average_price,
                quote.ohlc.open,
                quote.ohlc.high,
                quote.ohlc.low,
                quote.ohlc.close,
                json.dumps({"buy": [{"price": d.price, "quantity": d.quantity} for d in quote.depth.get("buy", [])],
                           "sell": [{"price": d.price, "quantity": d.quantity} for d in quote.depth.get("sell", [])]})
            ))
            conn.commit()
    
    def store_historical_data(self, historical: HistoricalData, timeframe: str = "day"):
        """Store historical OHLC data."""
        with self._get_connection() as conn:
            for _, row in historical.data.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO historical_data (
                        instrument_token, date, open, high, low, close, volume, timeframe
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    historical.instrument_token,
                    row.name if hasattr(row, 'name') else row['date'],
                    row['open'],
                    row['high'], 
                    row['low'],
                    row['close'],
                    row.get('volume', 0),
                    timeframe
                ))
            conn.commit()
    
    def get_quotes(self, instrument_tokens: List[int] = None, 
                  start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
        """Retrieve quote data with filtering."""
        query = """
            SELECT * FROM quotes 
            WHERE 1=1
        """
        params = []
        
        if instrument_tokens:
            placeholders = ','.join(['?'] * len(instrument_tokens))
            query += f" AND instrument_token IN ({placeholders})"
            params.extend(instrument_tokens)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC"
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_historical_data(self, instrument_token: int, 
                          start_date: datetime = None, 
                          end_date: datetime = None,
                          timeframe: str = "day") -> pd.DataFrame:
        """Retrieve historical OHLC data."""
        query = """
            SELECT * FROM historical_data 
            WHERE instrument_token = ? AND timeframe = ?
        """
        params = [instrument_token, timeframe]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date.date())
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date.date())
        
        query += " ORDER BY date"
        
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
    
    # Order Management Storage Methods  
    def store_order(self, order: Order):
        """Store order information."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO orders (
                    order_id, exchange_order_id, parent_order_id, tradingsymbol,
                    exchange, instrument_token, transaction_type, variety, product,
                    order_type, quantity, price, trigger_price, average_price,
                    pending_quantity, filled_quantity, cancelled_quantity,
                    disclosed_quantity, validity, validity_ttl, status, status_message,
                    order_timestamp, exchange_timestamp, exchange_update_timestamp,
                    placed_by, tag, guid, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.exchange_order_id, order.parent_order_id,
                order.tradingsymbol, order.exchange, order.instrument_token,
                order.transaction_type, order.variety, order.product, order.order_type,
                order.quantity, order.price, order.trigger_price, order.average_price,
                order.pending_quantity, order.filled_quantity, order.cancelled_quantity,
                order.disclosed_quantity, order.validity, order.validity_ttl,
                order.status, order.status_message, order.order_timestamp,
                order.exchange_timestamp, order.exchange_update_timestamp,
                order.placed_by, order.tag, order.guid, datetime.now()
            ))
            conn.commit()
    
    def store_trade(self, trade: Trade):
        """Store trade execution."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trades (
                    trade_id, order_id, exchange, tradingsymbol, instrument_token,
                    transaction_type, product, average_price, quantity, exchange_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id, trade.order_id, trade.exchange, trade.tradingsymbol,
                trade.instrument_token, trade.transaction_type, trade.product,
                trade.average_price, trade.quantity, trade.exchange_timestamp
            ))
            conn.commit()
    
    def get_orders(self, status: str = None, start_date: datetime = None) -> pd.DataFrame:
        """Retrieve orders with filtering."""
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if start_date:
            query += " AND order_timestamp >= ?"
            params.append(start_date)
        
        query += " ORDER BY order_timestamp DESC"
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    # Position and Holdings Storage
    def store_positions(self, positions: List[Position]):
        """Store position data."""
        with self._get_connection() as conn:
            for pos in positions:
                conn.execute("""
                    INSERT OR REPLACE INTO positions (
                        tradingsymbol, exchange, instrument_token, product, quantity,
                        overnight_quantity, multiplier, average_price, close_price,
                        last_price, value, pnl, m2m, unrealised, realised,
                        buy_quantity, buy_price, buy_value, buy_m2m,
                        sell_quantity, sell_price, sell_value, sell_m2m,
                        day_buy_quantity, day_buy_price, day_buy_value,
                        day_sell_quantity, day_sell_price, day_sell_value, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pos.tradingsymbol, pos.exchange, pos.instrument_token, pos.product,
                    pos.quantity, pos.overnight_quantity, pos.multiplier, pos.average_price,
                    pos.close_price, pos.last_price, pos.value, pos.pnl, pos.m2m,
                    pos.unrealised, pos.realised, pos.buy_quantity, pos.buy_price,
                    pos.buy_value, pos.buy_m2m, pos.sell_quantity, pos.sell_price,
                    pos.sell_value, pos.sell_m2m, pos.day_buy_quantity, pos.day_buy_price,
                    pos.day_buy_value, pos.day_sell_quantity, pos.day_sell_price,
                    pos.day_sell_value, datetime.now()
                ))
            conn.commit()
    
    def store_holdings(self, holdings: List[Holding]):
        """Store holdings data.""" 
        with self._get_connection() as conn:
            for holding in holdings:
                conn.execute("""
                    INSERT OR REPLACE INTO holdings (
                        tradingsymbol, exchange, instrument_token, isin, product,
                        price, quantity, used_quantity, t1_quantity, realised_quantity,
                        authorised_quantity, authorised_date, opening_quantity,
                        collateral_quantity, collateral_type, discrepancy,
                        average_price, last_price, close_price, pnl,
                        day_change, day_change_percentage, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    holding.tradingsymbol, holding.exchange, holding.instrument_token,
                    holding.isin, holding.product, holding.price, holding.quantity,
                    holding.used_quantity, holding.t1_quantity, holding.realised_quantity,
                    holding.authorised_quantity, holding.authorised_date,
                    holding.opening_quantity, holding.collateral_quantity,
                    holding.collateral_type, holding.discrepancy, holding.average_price,
                    holding.last_price, holding.close_price, holding.pnl,
                    holding.day_change, holding.day_change_percentage, datetime.now()
                ))
            conn.commit()
    
    def get_positions(self, date: datetime = None) -> pd.DataFrame:
        """Retrieve positions."""
        query = "SELECT * FROM positions WHERE 1=1"
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date.date())
        else:
            query += " AND date = DATE('now')"
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_holdings(self, date: datetime = None) -> pd.DataFrame:
        """Retrieve holdings."""
        query = "SELECT * FROM holdings WHERE 1=1" 
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date.date())
        else:
            query += " AND date = DATE('now')"
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    # GTT Storage
    def store_gtt_trigger(self, gtt: GTTTrigger):
        """Store GTT trigger."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO gtt_triggers (
                    id, user_id, type, created_at, updated_at, expires_at,
                    status, condition, orders
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gtt.id, gtt.user_id, gtt.type, gtt.created_at, gtt.updated_at,
                gtt.expires_at, gtt.status, json.dumps(gtt.condition), 
                json.dumps(gtt.orders)
            ))
            conn.commit()
    
    def get_gtt_triggers(self, status: str = None) -> pd.DataFrame:
        """Retrieve GTT triggers."""
        query = "SELECT * FROM gtt_triggers WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    # Mutual Fund Storage
    def store_mf_holdings(self, mf_holdings: List[MFHolding]):
        """Store mutual fund holdings."""
        with self._get_connection() as conn:
            for holding in mf_holdings:
                conn.execute("""
                    INSERT OR REPLACE INTO mf_holdings (
                        folio, fund, tradingsymbol, average_price, last_price,
                        last_price_date, pnl, quantity, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    holding.folio, holding.fund, holding.tradingsymbol,
                    holding.average_price, holding.last_price, holding.last_price_date,
                    holding.pnl, holding.quantity, datetime.now()
                ))
            conn.commit()
    
    # Portfolio Analytics
    def store_portfolio_snapshot(self, portfolio_data: Dict[str, Any]):
        """Store daily portfolio snapshot."""
        with self._get_connection() as conn:
            for segment, metrics in portfolio_data.items():
                if isinstance(metrics, dict):
                    for metric, value in metrics.items():
                        conn.execute("""
                            INSERT OR REPLACE INTO portfolio_snapshots (
                                date, segment, metric, value
                            ) VALUES (?, ?, ?, ?)
                        """, (datetime.now().date(), segment, metric, value))
            conn.commit()
    
    def get_portfolio_history(self, days: int = 30) -> pd.DataFrame:
        """Get portfolio performance history."""
        start_date = (datetime.now() - timedelta(days=days)).date()
        
        with self._get_connection() as conn:
            return pd.read_sql_query("""
                SELECT * FROM portfolio_snapshots 
                WHERE date >= ?
                ORDER BY date, segment, metric
            """, conn, params=[start_date])
    
    # Market Analysis Methods
    def calculate_daily_pnl(self, date: datetime = None) -> Dict[str, float]:
        """Calculate daily P&L summary."""
        if not date:
            date = datetime.now()
        
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT 
                    SUM(pnl) as total_pnl,
                    SUM(realised) as realised_pnl,
                    SUM(unrealised) as unrealised_pnl
                FROM positions 
                WHERE date = ?
            """, [date.date()]).fetchone()
            
            return {
                "total_pnl": result["total_pnl"] or 0,
                "realised_pnl": result["realised_pnl"] or 0,
                "unrealised_pnl": result["unrealised_pnl"] or 0
            }
    
    def get_top_gainers_losers(self, limit: int = 10) -> Dict[str, pd.DataFrame]:
        """Get top gainers and losers from holdings."""
        with self._get_connection() as conn:
            gainers = pd.read_sql_query("""
                SELECT tradingsymbol, day_change_percentage, pnl, last_price
                FROM holdings 
                WHERE date = DATE('now') AND day_change_percentage > 0
                ORDER BY day_change_percentage DESC
                LIMIT ?
            """, conn, params=[limit])
            
            losers = pd.read_sql_query("""
                SELECT tradingsymbol, day_change_percentage, pnl, last_price
                FROM holdings 
                WHERE date = DATE('now') AND day_change_percentage < 0
                ORDER BY day_change_percentage ASC
                LIMIT ?
            """, conn, params=[limit])
            
            return {"gainers": gainers, "losers": losers}
    
    # Cleanup and Maintenance
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data to maintain database performance."""
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        with self._get_connection() as conn:
            # Keep only recent quote data
            conn.execute("""
                DELETE FROM quotes 
                WHERE DATE(timestamp) < ?
            """, [cutoff_date])
            
            # Keep trade history but clean old order updates
            conn.execute("""
                DELETE FROM orders 
                WHERE DATE(order_timestamp) < ? AND status IN ('CANCELLED', 'REJECTED')
            """, [cutoff_date])
            
            conn.commit()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}
            
            tables = ['quotes', 'orders', 'trades', 'positions', 'holdings', 'gtt_triggers']
            for table in tables:
                count = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[f"{table}_count"] = count["count"]
            
            # Database size
            size = conn.execute("PRAGMA page_count").fetchone()[0]
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]
            stats["db_size_mb"] = (size * page_size) / (1024 * 1024)
            
            return stats
    
    def close(self):
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()