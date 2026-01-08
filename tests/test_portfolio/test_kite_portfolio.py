"""Unit tests for KitePortfolio."""

import pytest
from unittest.mock import Mock
import requests
from lib_zerodha.portfolio.kite_portfolio import KitePortfolio
from lib_zerodha.models.portfolio import Position, Holding

class TestKitePortfolio:
    @pytest.fixture
    def mock_session(self):
        return Mock(spec=requests.Session)

    @pytest.fixture
    def portfolio(self, mock_session):
        return KitePortfolio(
            session=mock_session,
            get_auth_headers=lambda: {"Authorization": "token key:token"}
        )

    def test_get_positions(self, portfolio, mock_session):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "net": [{"tradingsymbol": "SBIN", "exchange": "NSE", "instrument_token": 1, "product": "MIS", "quantity": 10, "buy_quantity": 10, "sell_quantity": 0, "buy_price": 500, "sell_price": 0, "buy_value": 5000, "sell_value": 0, "last_price": 510, "pnl": 100, "m2m": 100, "unrealised": 100, "realised": 0, "overnight_quantity": 0, "multiplier": 1, "average_price": 500, "close_price": 500, "value": 5000, "day_buy_quantity": 10, "day_buy_price": 500, "day_buy_value": 5000, "day_sell_quantity": 0, "day_sell_price": 0, "day_sell_value": 0, "buy_m2m": 100, "sell_m2m": 0}],
                "day": []
            }
        }
        mock_session.get.return_value = mock_response
        
        positions = portfolio.get_positions()
        assert len(positions["net"]) == 1
        assert positions["net"][0].tradingsymbol == "SBIN"

    def test_get_holdings(self, portfolio, mock_session):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [{"tradingsymbol": "INFY", "exchange": "NSE", "instrument_token": 2, "isin": "INE001", "product": "CNC", "quantity": 5, "t1_quantity": 0, "realised_quantity": 5, "authorised_quantity": 5, "average_price": 1400, "last_price": 1410, "pnl": 50, "day_change": 10, "day_change_percentage": 0.7}]
        }
        mock_session.get.return_value = mock_response
        
        holdings = portfolio.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].tradingsymbol == "INFY"

    def test_convert_position(self, portfolio, mock_session):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": True}
        mock_session.put.return_value = mock_response
        
        result = portfolio.convert_position(
            tradingsymbol="SBIN",
            exchange="NSE",
            transaction_type="BUY",
            position_type="day",
            quantity=10,
            old_product="MIS",
            new_product="CNC"
        )
        assert result is True
