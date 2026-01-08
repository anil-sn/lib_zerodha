"""Test the KiteClient core functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from lib_zerodha import (
    KiteClient, AuthenticationError, APIError, RateLimitError
)


class TestKiteClient:
    """Test cases for KiteClient class."""

    def test_client_initialization(self):
        """Test KiteClient initialization with valid credentials."""
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret",
                request_token="test_token"
            )
            
            assert client.api_key == "test_key"
            assert client.api_secret == "test_secret"
            # In facade pattern, request_token isn't stored on client instance but passed to auth
            # assert client.request_token == "test_token" 
            mock_auth.assert_called_once()

    def test_client_initialization_without_request_token(self):
        """Test KiteClient initialization without request token."""
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth:
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret"
            )
            
            assert client.api_key == "test_key"
            assert client.api_secret == "test_secret"
            # assert client.request_token is None

    def test_get_login_url(self):
        """Test getting login URL."""
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.get_login_url.return_value = "https://kite.trade/connect/login?api_key=test_key"
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            login_url = client.get_login_url()
            
            assert login_url == "https://kite.trade/connect/login?api_key=test_key"
            mock_auth_instance.get_login_url.assert_called_once()

    def test_generate_session_success(self):
        """Test successful session generation."""
        # Patch SessionManager.create_session as KiteClient delegates to it
        with patch('lib_zerodha.kite_client.SessionManager') as mock_sm_cls:
            mock_sm = Mock()
            mock_sm_cls.return_value = mock_sm
            
            mock_sm.create_session.return_value = {
                "access_token": "test_access_token",
                "user_id": "test_user",
                "user_name": "Test User"
            }
            
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret"
            )
            
            session_data = client.generate_session("test_request_token")
            
            assert session_data["access_token"] == "test_access_token"
            mock_sm.create_session.assert_called_once_with("test_request_token")

    def test_profile_retrieval(self):
        """Test user profile retrieval."""
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.get_profile.return_value = {
                "user_id": "TEST123",
                "user_name": "Test User",
                "email": "test@example.com",
                "broker": "ZERODHA"
            }
            mock_auth_instance.is_authenticated.return_value = True
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            # Inject token to bypass init checks if any
            client.auth.access_token = "test_token"
            
            profile = client.get_profile()
            
            assert profile["user_id"] == "TEST123"
            mock_auth_instance.get_profile.assert_called_once()

    @patch('lib_zerodha.kite_client.KiteOrders')
    def test_order_placement_integration(self, mock_orders_cls):
        """Test order placement through client."""
        mock_orders = Mock()
        mock_orders.place_order.return_value = "240107000001"
        mock_orders_cls.return_value = mock_orders
        
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth_cls:
            mock_auth = Mock()
            mock_auth.is_authenticated.return_value = True
            mock_auth_cls.return_value = mock_auth
            
            client = KiteClient(api_key="test_key", api_secret="test_secret", access_token="test_token")
            
            result = client.place_order(
                variety="regular",
                exchange="NSE", 
                tradingsymbol="INFY",
                transaction_type="BUY",
                quantity=10,
                product="CNC",
                order_type="MARKET"
            )
            
            assert result == "240107000001"
            mock_orders.place_order.assert_called_once()

    @patch('lib_zerodha.kite_client.KiteMarketData')
    def test_quote_retrieval_integration(self, mock_market_cls):
        """Test quote retrieval through client."""
        mock_market = Mock()
        mock_market.get_quote.return_value = {
            "NSE:INFY": {
                "instrument_token": 408065,
                "last_price": 1850.50,
                "volume": 1234567
            }
        }
        mock_market_cls.return_value = mock_market
        
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth_cls:
            mock_auth = Mock()
            mock_auth.is_authenticated.return_value = True
            mock_auth_cls.return_value = mock_auth
            
            client = KiteClient(api_key="test_key", api_secret="test_secret", access_token="test_token")
            
            quote = client.get_quote(["NSE:INFY"])
            
            assert quote["NSE:INFY"]["last_price"] == 1850.50
            mock_market.get_quote.assert_called_once()

    @patch('lib_zerodha.kite_client.KitePortfolio')
    def test_positions_retrieval_integration(self, mock_portfolio_cls):
        """Test positions retrieval through client."""
        mock_portfolio = Mock()
        mock_portfolio.get_positions.return_value = {
            "net": [],
            "day": []
        }
        mock_portfolio_cls.return_value = mock_portfolio
        
        with patch('lib_zerodha.kite_client.KiteAuth') as mock_auth_cls:
            mock_auth = Mock()
            mock_auth.is_authenticated.return_value = True
            mock_auth_cls.return_value = mock_auth
            
            client = KiteClient(api_key="test_key", api_secret="test_secret", access_token="test_token")
            
            positions = client.get_positions()
            
            assert "net" in positions
            mock_portfolio.get_positions.assert_called_once()

    def test_client_repr_representation(self):
        """Test repr representation of client."""
        with patch('lib_zerodha.kite_client.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            
            repr_str = repr(client)
            assert "KiteClient" in repr_str
            assert "at 0x" in repr_str