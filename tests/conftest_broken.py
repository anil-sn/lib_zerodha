"""Test configuration and shared fixtures for lib_zerodha."""

import json
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch
from typing import Dict, Any


# Mock API responses for testing
MOCK_PROFILE_RESPONSE = {
    "user_id": "TEST123",
    "user_name": "Test User", 
    "user_shortname": "Test",
    "email": "test@example.com",
    "user_type": "individual",
    "broker": "ZERODHA",
    "exchanges": ["NSE", "BSE", "NFO", "BFO", "CDS", "MCX"],
    "products": ["CNC", "MIS", "NRML"],
    "order_types": ["MARKET", "LIMIT", "SL", "SL-M"],
    "avatar_url": None,
    "meta": {
        "demat_consent": "physical"
    }
}

MOCK_INSTRUMENTS_DATA = [
        {
            "instrument_token": 256265,
            "exchange_token": 1001,
            "tradingsymbol": "RELIANCE",
            "name": "RELIANCE INDUSTRIES LTD",
            "last_price": 2650.0,
            "expiry": "",
            "strike": 0.0,
            "tick_size": 0.05,
            "lot_size": 1,
            "instrument_type": "EQ",
            "segment": "NSE",
            "exchange": "NSE"
        },
        {
            "instrument_token": 408065,
            "exchange_token": 1594,
            "tradingsymbol": "INFY",
            "name": "INFOSYS LIMITED",
            "last_price": 1750.0,
            "expiry": "",
            "strike": 0.0,
            "tick_size": 0.05,
            "lot_size": 1,
            "instrument_type": "EQ",
            "segment": "NSE",
            "exchange": "NSE"
        }
    ]


@pytest.fixture
def sample_orders():
    """Sample order data for testing."""
    return [
        {
            "order_id": "ORDER001",
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": 2650.0,
            "product": "MIS",
            "status": "COMPLETE",
            "filled_quantity": 10,
            "average_price": 2650.0
        }
    ]


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing real-time features."""
    with patch('websocket.WebSocketApp') as mock_ws:
        yield mock_ws