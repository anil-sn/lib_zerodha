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
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret",
                request_token="test_token"
            )
            
            assert client.api_key == "test_key"
            assert client.api_secret == "test_secret"
            assert client.request_token == "test_token"
            mock_auth.assert_called_once()

    def test_client_initialization_without_request_token(self):
        """Test KiteClient initialization without request token."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret"
            )
            
            assert client.api_key == "test_key"
            assert client.api_secret == "test_secret"
            assert client.request_token is None

    def test_get_login_url(self):
        """Test getting login URL."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.login_url.return_value = "https://kite.trade/connect/login?api_key=test_key"
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            login_url = client.get_login_url()
            
            assert login_url == "https://kite.trade/connect/login?api_key=test_key&v=3"
            mock_auth_instance.login_url.assert_called_once()

    def test_generate_session_success(self):
        """Test successful session generation."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.generate_session.return_value = {
                "access_token": "test_access_token",
                "user_id": "test_user",
                "user_name": "Test User"
            }
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret",
                request_token="test_token"
            )
            
            session_data = client.generate_session("test_request_token")
            
            assert session_data["access_token"] == "test_access_token"
            assert session_data["user_id"] == "test_user"
            assert client.access_token == "test_access_token"
            mock_auth_instance.generate_session.assert_called_once_with("test_token")

    def test_generate_session_auth_error(self):
        """Test session generation with authentication error."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.generate_session.side_effect = Exception("Invalid token")
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(
                api_key="test_key",
                api_secret="test_secret",
                request_token="invalid_token"
            )
            
            with pytest.raises(AuthenticationError):
                client.generate_session("invalid_request_token")

    def test_profile_retrieval(self):
        """Test user profile retrieval."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.profile.return_value = {
                "user_id": "TEST123",
                "user_name": "Test User",
                "email": "test@example.com",
                "broker": "ZERODHA"
            }
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            profile = client.get_profile()
            
            assert profile["user_id"] == "TEST123"
            assert profile["user_name"] == "Test User"
            assert profile["email"] == "test@example.com"
            mock_auth_instance.profile.assert_called_once()

    @patch('lib_zerodha.orders.kite_orders.KiteOrders')
    def test_order_placement_integration(self, mock_orders):
        """Test order placement through client."""
        mock_orders_instance = Mock()
        mock_orders_instance.place_order.return_value = {"order_id": "240107000001"}
        mock_orders.return_value = mock_orders_instance
        
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            result = client.place_order(
                variety="regular",
                exchange="NSE", 
                tradingsymbol="INFY",
                transaction_type="BUY",
                quantity=10,
                product="CNC",
                order_type="MARKET"
            )
            
            assert result["order_id"] == "240107000001"
            mock_orders_instance.place_order.assert_called_once()

    @patch('lib_zerodha.market_data.kite_market_data.KiteMarketData')
    def test_quote_retrieval_integration(self, mock_market_data):
        """Test quote retrieval through client."""
        mock_market_data_instance = Mock()
        mock_market_data_instance.get_quote.return_value = {
            "NSE:INFY": {
                "instrument_token": 408065,
                "last_price": 1850.50,
                "volume": 1234567
            }
        }
        mock_market_data.return_value = mock_market_data_instance
        
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            quote = client.get_quote(["NSE:INFY"])
            
            assert quote["NSE:INFY"]["last_price"] == 1850.50
            assert quote["NSE:INFY"]["instrument_token"] == 408065
            mock_market_data_instance.get_quote.assert_called_once_with(["NSE:INFY"])

    @patch('lib_zerodha.portfolio.kite_portfolio.KitePortfolio')
    def test_positions_retrieval_integration(self, mock_portfolio):
        """Test positions retrieval through client."""
        mock_portfolio_instance = Mock()
        mock_portfolio_instance.get_positions.return_value = {
            "net": [
                {
                    "tradingsymbol": "INFY",
                    "exchange": "NSE",
                    "quantity": 10,
                    "average_price": 1845.50,
                    "pnl": 50.00
                }
            ],
            "day": []
        }
        mock_portfolio.return_value = mock_portfolio_instance
        
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            positions = client.get_positions()
            
            assert len(positions["net"]) == 1
            assert positions["net"][0]["tradingsymbol"] == "INFY"
            assert positions["net"][0]["pnl"] == 50.00
            mock_portfolio_instance.get_positions.assert_called_once()

    def test_client_without_access_token_raises_error(self):
        """Test that API calls without access token raise error."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            # No access_token set
            
            with pytest.raises(AuthenticationError, match="Access token required"):
                client.get_profile()

    def test_api_error_handling(self):
        """Test API error handling and exception raising."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            # Simulate API error
            mock_auth_instance.profile.side_effect = Exception("NetworkError")
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            with pytest.raises(APIError):
                client.get_profile()

    def test_rate_limit_handling(self):
        """Test rate limit error handling."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth') as mock_auth:
            mock_auth_instance = Mock()
            # Simulate rate limit error
            mock_auth_instance.profile.side_effect = Exception("Too Many Requests")
            mock_auth.return_value = mock_auth_instance
            
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            client.access_token = "test_token"
            
            with pytest.raises(APIError):  # Should be caught as APIError for now
                client.get_profile()

    def test_client_str_representation(self):
        """Test string representation of client."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            
            str_repr = str(client)
            assert "KiteClient" in str_repr
            assert "test_key" in str_repr

    def test_client_repr_representation(self):
        """Test repr representation of client."""
        with patch('lib_zerodha.auth.kite_auth.KiteAuth'):
            client = KiteClient(api_key="test_key", api_secret="test_secret")
            
            repr_str = repr(client)
            assert "KiteClient" in repr_str
            assert "api_key=" in repr_str