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

MOCK_QUOTE_RESPONSE = {
    "NSE:INFY": {
        "instrument_token": 408065,
        "timestamp": "2025-01-07T15:30:00+05:30",
        "last_price": 1850.50,
        "last_quantity": 100,
        "last_trade_time": "2025-01-07T15:29:58+05:30",
        "average_price": 1845.25,
        "volume": 1234567,
        "buy_quantity": 500000,
        "sell_quantity": 450000,
        "ohlc": {
            "open": 1842.00,
            "high": 1856.75,
            "low": 1838.50,
            "close": 1849.25
        },
        "net_change": 1.25,
        "oi": 0,
        "oi_day_high": 0,
        "oi_day_low": 0,
        "depth": {
            "buy": [
                {"quantity": 100, "price": 1850.00, "orders": 5},
                {"quantity": 200, "price": 1849.50, "orders": 3}
            ],
            "sell": [
                {"quantity": 125, "price": 1851.00, "orders": 6},
                {"quantity": 175, "price": 1851.50, "orders": 4}
            ]
        }
    }
}

@pytest.fixture
def mock_kite_client():
    """Mock KiteConnect client for testing."""
    mock_client = Mock()
    
    # Mock API responses
    mock_client.profile.return_value = MOCK_PROFILE_RESPONSE
    mock_client.quote.return_value = MOCK_QUOTE_RESPONSE
    
    return mock_client

@pytest.fixture  
def api_helper():
    """API testing helper fixture."""
    class APITestHelper:
        @staticmethod
        def create_mock_response(status_code: int, json_data: Dict[str, Any]):
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = json_data
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.text = json.dumps(json_data)
            return mock_response
    
    return APITestHelper()