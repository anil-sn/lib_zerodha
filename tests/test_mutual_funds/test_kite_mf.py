"""Tests for KiteMF module."""

import pytest
from unittest.mock import Mock
import requests

from lib_zerodha import OrderError, ValidationError, NetworkError
from lib_zerodha.mutual_funds.kite_mf import KiteMF


class TestKiteMF:
    """Test cases for KiteMF class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        session = Mock(spec=requests.Session)
        session.headers = {}
        return session
    
    @pytest.fixture
    def mf(self, mock_session):
        """Create KiteMF instance."""
        return KiteMF(
            session=mock_session,
            get_auth_headers=lambda: {"Authorization": "token test_api_key:test_token"}
        )
    
    def test_place_order_success(self, mf, mock_session):
        """Test successful MF order placement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "123456"}
        }
        mock_session.post.return_value = mock_response
        
        order_id = mf.place_order(
            tradingsymbol="INF174K01LS2",
            transaction_type="BUY",
            amount=5000.0
        )
        
        assert order_id == "123456"
        mock_session.post.assert_called_once()
        
        # Verify payload
        call_args = mock_session.post.call_args
        data = call_args[1]['data']
        assert data['tradingsymbol'] == "INF174K01LS2"
        assert data['transaction_type'] == "BUY"
        assert data['amount'] == 5000.0

    def test_place_order_sell_validation(self, mf):
        """Test validation for SELL order (quantity required)."""
        with pytest.raises(ValidationError, match="Quantity is required"):
            mf.place_order(
                tradingsymbol="INF174K01LS2",
                transaction_type="SELL",
                amount=5000.0 # Should provide quantity, not amount (or maybe both but logic says check quantity)
            )

    def test_get_orders_success(self, mf, mock_session):
        """Test fetching MF orders."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "order_id": "1",
                    "tradingsymbol": "FUND1",
                    "status": "OPEN",
                    "transaction_type": "BUY"
                }
            ]
        }
        mock_session.get.return_value = mock_response
        
        orders = mf.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "1"
        assert orders[0].tradingsymbol == "FUND1"

    def test_place_sip_success(self, mf, mock_session):
        """Test successful SIP placement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"sip_id": "987654"}
        }
        mock_session.post.return_value = mock_response
        
        sip_id = mf.place_sip(
            tradingsymbol="INF174K01LS2",
            amount=1000.0,
            instalments=12,
            frequency="monthly",
            instalment_day=10
        )
        
        assert sip_id == "987654"
        mock_session.post.assert_called_once()

    def test_get_holdings_success(self, mf, mock_session):
        """Test fetching MF holdings."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "folio": "123/456",
                    "fund": "Test Fund",
                    "tradingsymbol": "TESTFUND",
                    "average_price": 10.0,
                    "last_price": 12.0,
                    "pnl": 200.0,
                    "quantity": 100.0
                }
            ]
        }
        mock_session.get.return_value = mock_response
        
        holdings = mf.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].tradingsymbol == "TESTFUND"
        assert holdings[0].quantity == 100.0

    def test_api_error_handling(self, mf, mock_session):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "message": "Invalid symbol"
        }
        mock_session.post.return_value = mock_response
        
        with pytest.raises(OrderError, match="Invalid symbol"):
            mf.place_order(
                tradingsymbol="INVALID",
                transaction_type="BUY",
                amount=1000
            )
