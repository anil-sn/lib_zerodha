"""Tests for KiteAuth authentication module."""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from lib_zerodha import (
    KiteAuth, AuthenticationError, SessionExpiredError, 
    InvalidCredentialsError, NetworkError
)


class TestKiteAuth:
    """Test cases for KiteAuth class."""
    
    @pytest.fixture
    def auth(self, test_config):
        """Create KiteAuth instance for testing."""
        return KiteAuth(
            api_key="test_api_key",
            api_secret="test_api_secret"
        )
    
    def test_init(self, auth):
        """Test KiteAuth initialization."""
        assert auth.api_key == "test_api_key"
        assert auth.api_secret == "test_api_secret"
        assert auth.access_token is None
        assert not auth.is_session_valid()
    
    def test_get_login_url(self, auth):
        """Test login URL generation."""
        url = auth.get_login_url()
        
        assert "kite.trade/connect/login" in url
        assert "api_key=test_api_key" in url
    
    @patch('requests.Session.post')
    def test_generate_session_success(self, mock_post, auth, mock_login_response):
        """Test successful session generation."""
        mock_post.return_value.json.return_value = mock_login_response
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = Mock()
        
        session_data = auth.generate_session("test_request_token")
        
        assert "access_token" in session_data
        assert auth.access_token == "XXXXXX"
        assert auth.is_session_valid()
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "session/token" in call_args[0][0]
    
    @patch('requests.Session.post')
    def test_generate_session_invalid_token(self, mock_post, auth):
        """Test session generation with invalid request token."""
        error_response = {
            "status": "error",
            "message": "Invalid request token",
            "error_type": "TokenException"
        }
        
        mock_post.return_value.json.return_value = error_response
        mock_post.return_value.status_code = 400
        mock_post.return_value.raise_for_status = Mock(side_effect=requests.exceptions.HTTPError("400 Client Error"))
        
        with pytest.raises(NetworkError):
            auth.generate_session("invalid_token")
        
        assert not auth.is_session_valid()
    
    def test_set_access_token(self, auth):
        """Test setting access token directly."""
        auth.access_token = "direct_access_token"
        
        assert auth.access_token == "direct_access_token"
        assert auth.is_session_valid()
    
    @patch('requests.Session.request')
    def test_get_profile_success(self, mock_request, auth, mock_profile_response):
        """Test successful profile retrieval."""
        auth.access_token = "test_token"
        
        mock_request.return_value.json.return_value = mock_profile_response
        mock_request.return_value.status_code = 200
        mock_request.return_value.raise_for_status = Mock()
        
        profile = auth.get_profile()
        
        assert profile["user_id"] == "AB1234"
        assert profile["user_name"] == "AxAx Bxx"
    
    @patch('requests.Session.request')
    def test_get_profile_unauthenticated(self, mock_request, auth):
        """Test profile retrieval without authentication."""
        with pytest.raises(AuthenticationError):
            auth.get_profile()
    
    @patch('requests.Session.request')
    def test_get_profile_expired_token(self, mock_request, auth):
        """Test profile retrieval with expired token."""
        auth.access_token = "expired_token"
        
        error_response = {
            "status": "error",
            "message": "Token has expired",
            "error_type": "TokenException"
        }
        
        mock_request.return_value.json.return_value = error_response
        mock_request.return_value.status_code = 403
        
        # We need to simulate the response object having the json data for ErrorHandler to find it
        mock_resp = Mock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = error_response
        mock_resp.headers = {'content-type': 'application/json'}
        mock_request.return_value = mock_resp
        
        # The code uses raise_for_status() which we need to trigger
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with pytest.raises(SessionExpiredError):
            auth.get_profile()
    
    @patch('requests.Session.delete')
    def test_logout(self, mock_delete, auth):
        """Test logout functionality."""
        auth.access_token = "test_token"
        mock_delete.return_value.status_code = 200
        
        auth.logout()
        
        assert auth.access_token is None
        assert not auth.is_authenticated()
    
    def test_validate_session_valid(self, auth):
        """Test session validation with valid token."""
        auth.access_token = "valid_token"
        assert auth.validate_session()
    
    def test_validate_session_invalid(self, auth):
        """Test session validation with invalid token."""
        auth.access_token = None
        assert not auth.validate_session()
    
    def test_session_expiry_handling(self, auth):
        """Test automatic session expiry handling."""
        # Set session with expiry time in the past
        auth.access_token = "expired_token"
        auth.session_expiry = datetime.now() - timedelta(minutes=30)
        
        assert not auth.is_session_valid()
        
        # Set session with future expiry
        auth.session_expiry = datetime.now() + timedelta(minutes=30)
        assert auth.is_session_valid()
    
    def test_api_request_with_auth_headers(self, auth):
        """Test API request includes proper authentication headers."""
        auth.access_token = "test_token"
        
        with patch('requests.Session.request') as mock_request:
            mock_request.return_value.json.return_value = {"status": "success"}
            mock_request.return_value.status_code = 200
            mock_request.return_value.raise_for_status = Mock()
            
            auth._make_request('GET', '/test')
            
            # Verify headers
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            
            assert 'Authorization' in headers
            assert headers['Authorization'] == 'token test_api_key:test_token'
            assert headers['X-Kite-Version'] == '3'
    
    @pytest.mark.parametrize("status_code,expected_exception", [
        (401, AuthenticationError),
        (403, SessionExpiredError),
        (400, InvalidCredentialsError),
    ])
    def test_error_handling(self, auth, status_code, expected_exception):
        """Test different error status codes."""
        auth.access_token = "test_token"
        
        with patch('requests.Session.request') as mock_request:
            mock_resp = Mock()
            mock_resp.status_code = status_code
            mock_resp.json.return_value = {
                "status": "error",
                "message": "Test error",
                "error_type": "GeneralException"
            }
            mock_resp.headers = {'content-type': 'application/json'}
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)
            mock_request.return_value = mock_resp
            
            with pytest.raises(expected_exception):
                auth._make_request('GET', '/test')
            
            mock_request.assert_called_once()
