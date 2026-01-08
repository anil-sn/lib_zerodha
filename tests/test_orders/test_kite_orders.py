"""Tests for KiteOrders module."""

import pytest
from unittest.mock import Mock, patch
import requests
import json

from lib_zerodha import KiteOrders, OrderError, ValidationError, NetworkError


class TestKiteOrders:
    """Test cases for KiteOrders class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock requests session."""
        session = Mock(spec=requests.Session)
        session.headers = {}
        return session
    
    @pytest.fixture
    def orders(self, mock_session):
        """Create KiteOrders instance."""
        return KiteOrders(
            session=mock_session,
            get_auth_headers=lambda: {"Authorization": "token test_api_key:test_token"}
        )
    
    def test_place_order_success(self, orders, mock_session):
        """Test successful order placement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "240107000001"}
        }
        mock_session.post.return_value = mock_response
        
        order_id = orders.place_order(
            tradingsymbol="INFY",
            exchange="NSE",
            transaction_type="BUY",
            quantity=1,
            order_type="MARKET",
            product="CNC"
        )
        
        assert order_id == "240107000001"
        mock_session.post.assert_called_once()
    
    def test_place_order_validation_error(self, orders):
        """Test order validation failure."""
        with pytest.raises(ValidationError):
            orders.place_order(
                tradingsymbol="INFY",
                exchange="INVALID",
                transaction_type="BUY",
                quantity=1,
                order_type="MARKET",
                product="CNC"
            )
            
    def test_place_order_api_error(self, orders, mock_session):
        """Test API error during order placement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "message": "Insufficient funds",
            "error_type": "OrderException"
        }
        mock_session.post.return_value = mock_response
        
        with pytest.raises(OrderError, match="Insufficient funds"):
            orders.place_order(
                tradingsymbol="INFY",
                exchange="NSE",
                transaction_type="BUY",
                quantity=1,
                order_type="MARKET",
                product="CNC"
            )
            
    def test_modify_order_success(self, orders, mock_session):
        """Test successful order modification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "240107000001"}
        }
        mock_session.put.return_value = mock_response
        
        order_id = orders.modify_order(
            order_id="240107000001",
            quantity=10,
            price=1500.0
        )
        
        assert order_id == "240107000001"
        mock_session.put.assert_called_once()
        
    def test_cancel_order_success(self, orders, mock_session):
        """Test successful order cancellation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "240107000001"}
        }
        mock_session.delete.return_value = mock_response
        
        order_id = orders.cancel_order("240107000001")
        
        assert order_id == "240107000001"
        mock_session.delete.assert_called_once()
        
    def test_get_orders_success(self, orders, mock_session):
        """Test successful retrieval of order book."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"order_id": "1", "status": "COMPLETE"},
                {"order_id": "2", "status": "OPEN"}
            ]
        }
        mock_session.get.return_value = mock_response
        
        orders_list = orders.get_orders()
        
        assert len(orders_list) == 2
        assert orders_list[0]["order_id"] == "1"
        
    def test_network_error_handling(self, orders, mock_session):
        """Test network error handling."""
        mock_session.post.side_effect = requests.exceptions.RequestException("Connection failed")
        
        with pytest.raises(NetworkError, match="Network error"):
            orders.place_order(
                tradingsymbol="INFY",
                exchange="NSE",
                transaction_type="BUY",
                quantity=1,
                order_type="MARKET",
                product="CNC"
            )

    # --- GTT Tests ---

    def test_place_gtt_success(self, orders, mock_session):
        """Test successful GTT placement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"trigger_id": 12345}
        }
        mock_session.post.return_value = mock_response
        
        trigger_id = orders.place_gtt(
            trigger_type="single",
            tradingsymbol="INFY",
            exchange="NSE",
            trigger_values=[1600.0],
            last_price=1500.0,
            orders=[{"transaction_type": "BUY", "quantity": 1, "price": 1600, "order_type": "LIMIT", "product": "CNC"}]
        )
        
        assert trigger_id["trigger_id"] == 12345
        mock_session.post.assert_called_once()
        
        # Verify payload structure
        call_args = mock_session.post.call_args
        data = call_args[1]['data']
        assert data['type'] == 'single'
        condition = json.loads(data['condition'])
        assert condition['trigger_values'] == [1600.0]

    def test_place_gtt_validation(self, orders):
        """Test GTT validation for invalid trigger type."""
        with pytest.raises(ValidationError, match="Invalid trigger_type"):
            orders.place_gtt(
                trigger_type="triple", # Invalid
                tradingsymbol="INFY",
                exchange="NSE",
                trigger_values=[1600.0],
                last_price=1500.0,
                orders=[]
            )

    def test_get_gtts_success(self, orders, mock_session):
        """Test fetching GTT list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [{"id": 1}, {"id": 2}]
        }
        mock_session.get.return_value = mock_response
        
        gtts = orders.get_gtts()
        assert len(gtts) == 2
        assert gtts[0]["id"] == 1

    def test_delete_gtt_success(self, orders, mock_session):
        """Test GTT deletion."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"trigger_id": 123}
        }
        mock_session.delete.return_value = mock_response
        
        result = orders.delete_gtt(123)
        assert result["trigger_id"] == 123
        mock_session.delete.assert_called_once()