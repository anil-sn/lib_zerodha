"""Tests for KiteMarketData module."""

import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import Mock, patch
from lib_zerodha.market_data.kite_market_data import KiteMarketData
from lib_zerodha.exceptions import APIError, ValidationError, NetworkError
from lib_zerodha.models.market_data import Quote, OHLC

class TestKiteMarketData:
    """Test cases for KiteMarketData class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        session = Mock()
        session.headers = {}
        return session

    @pytest.fixture
    def mock_get_auth_headers(self):
        """Mock function for getting auth headers."""
        return lambda: {'Authorization': 'token test_api_key:test_token'}

    @pytest.fixture
    def market_data(self, mock_session, mock_get_auth_headers):
        """Create KiteMarketData instance."""
        return KiteMarketData(mock_session, mock_get_auth_headers)

    def test_get_quote_success(self, market_data, mock_session):
        """Test successful quote retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "NSE:INFY": {
                    "instrument_token": 408065,
                    "timestamp": "2025-01-07 15:30:00",
                    "last_price": 1850.50,
                    "volume": 1000,
                    "ohlc": {
                        "open": 1840.0,
                        "high": 1860.0,
                        "low": 1835.0,
                        "close": 1845.0
                    }
                }
            }
        }
        mock_session.get.return_value = mock_response

        quotes = market_data.get_quote(["NSE:INFY"])

        assert "NSE:INFY" in quotes
        quote = quotes["NSE:INFY"]
        assert isinstance(quote, Quote)
        assert quote.last_price == 1850.50
        assert quote.instrument_token == 408065
        
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[1]['params']['i'] == ["NSE:INFY"]

    def test_get_quote_invalid_instrument(self, market_data):
        """Test validation for invalid instrument format."""
        with pytest.raises(ValidationError, match="Invalid instrument format"):
            market_data.get_quote(["INFY"])  # Missing exchange

    def test_get_ltp_success(self, market_data, mock_session):
        """Test successful LTP retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "NSE:INFY": {"last_price": 1850.50},
                "NSE:TCS": {"last_price": 3500.00}
            }
        }
        mock_session.get.return_value = mock_response

        ltp_data = market_data.get_ltp(["NSE:INFY", "NSE:TCS"])

        assert ltp_data["NSE:INFY"] == 1850.50
        assert ltp_data["NSE:TCS"] == 3500.00

    def test_get_ohlc_success(self, market_data, mock_session):
        """Test successful OHLC retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "NSE:INFY": {
                    "instrument_token": 408065,
                    "last_price": 1850.50,
                    "ohlc": {
                        "open": 1840.0,
                        "high": 1860.0,
                        "low": 1835.0,
                        "close": 1845.0
                    }
                }
            }
        }
        mock_session.get.return_value = mock_response

        ohlc_data = market_data.get_ohlc(["NSE:INFY"])

        assert "NSE:INFY" in ohlc_data
        ohlc = ohlc_data["NSE:INFY"]
        assert isinstance(ohlc, OHLC)
        assert ohlc.open == 1840.0
        assert ohlc.close == 1845.0

    def test_get_historical_data_success(self, market_data, mock_session):
        """Test successful historical data retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "candles": [
                    ["2025-01-01T09:15:00+0530", 100, 105, 95, 102, 5000],
                    ["2025-01-01T09:16:00+0530", 102, 108, 101, 107, 6000]
                ]
            }
        }
        mock_session.get.return_value = mock_response

        df = market_data.get_historical_data(
            instrument_token=408065,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 1),
            interval="minute"
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "open" in df.columns
        assert "volume" in df.columns
        assert df.iloc[0]["close"] == 102

    def test_get_historical_data_invalid_interval(self, market_data):
        """Test validation for invalid interval."""
        with pytest.raises(ValidationError, match="Invalid interval"):
            market_data.get_historical_data(
                instrument_token=408065,
                from_date=date(2025, 1, 1),
                to_date=date(2025, 1, 1),
                interval="invalid_interval"
            )

    def test_get_instruments_success(self, market_data, mock_session):
        """Test successful instruments retrieval (CSV format)."""
        csv_content = (
            "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n"
            "408065,1594,INFY,INFOSYS,1850.5,,0,0.05,1,EQ,NSE,NSE\n"
            "2953217,11483,NIFTY25JANFUT,NIFTY,24500.0,2025-01-30,0,0.05,50,FUT,NFO,NFO"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = csv_content.encode('utf-8')
        mock_response.text = csv_content
        mock_session.get.return_value = mock_response

        df = market_data.get_instruments(exchange="NSE")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "instrument_token" in df.columns
        assert df.iloc[0]["tradingsymbol"] == "INFY"
        
        mock_session.get.assert_called_once()
        assert "instruments/NSE" in mock_session.get.call_args[0][0]

    def test_api_error_handling(self, market_data, mock_session):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 200  # API returns 200 but status='error' in JSON
        mock_response.json.return_value = {
            "status": "error",
            "message": "Instrument not found",
            "error_type": "InputException"
        }
        mock_session.get.return_value = mock_response

        with pytest.raises(APIError, match="Instrument not found"):
            market_data.get_quote(["NSE:INVALID"])
