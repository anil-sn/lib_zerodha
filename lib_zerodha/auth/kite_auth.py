"""Authentication and session management for Kite Connect API."""

import hashlib
import urllib.parse
from typing import Dict, Optional, Any
import requests
from datetime import datetime, timedelta

from ..exceptions import AuthenticationError, NetworkError, APIError, SessionExpiredError, InvalidCredentialsError


class KiteAuth:
    """Handles Kite Connect authentication and session management."""
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None, config: Any = None):
        """Initialize authentication handler.
        
        Args:
            api_key: Kite Connect API key
            api_secret: API secret for token generation
            config: Configuration object
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config
        self.access_token: Optional[str] = None
        self.session_expiry: Optional[datetime] = None
        self.user_profile: Optional[Dict[str, Any]] = None
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'lib_zerodha/1.0.0',
            'X-Kite-Version': '3'
        })
    
    def get_login_url(self) -> str:
        """Generate login URL for Kite Connect authentication.
        
        Returns:
            Login URL for user authentication
        """
        params = {
            'api_key': self.api_key,
            'v': '3'
        }
        return f"{self.config.LOGIN_URL}?{urllib.parse.urlencode(params)}"
    
    def generate_session(self, request_token: str, api_secret: Optional[str] = None) -> Dict[str, str]:
        """Generate access token from request token.
        
        Args:
            request_token: Request token from Kite login flow
            api_secret: API secret (optional if provided in constructor)
            
        Returns:
            Dictionary containing access token and user info
            
        Raises:
            AuthenticationError: If token generation fails
            NetworkError: If network request fails
        """
        secret = api_secret or self.api_secret
        if not secret:
            raise AuthenticationError("API secret is required for token generation")
        
        # Generate checksum
        checksum = hashlib.sha256(
            f"{self.api_key}{request_token}{secret}".encode()
        ).hexdigest()
        
        data = {
            'api_key': self.api_key,
            'request_token': request_token,
            'checksum': checksum
        }
        
        try:
            response = self.session.post(
                f"{self.config.base_url}/session/token",
                data=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise AuthenticationError(
                    result.get('message', 'Token generation failed'),
                    result.get('error_type')
                )
            
            # Extract session data
            data = result.get('data', {})
            self.access_token = data.get('access_token')
            self.user_profile = data.get('user_profile', {})
            
            # Set session expiry (tokens typically expire at 6 AM next day)
            now = datetime.now()
            next_day_6am = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
            self.session_expiry = next_day_6am
            
            return {
                'access_token': self.access_token,
                'user_id': self.user_profile.get('user_id'),
                'user_name': self.user_profile.get('user_name'),
                'email': self.user_profile.get('email'),
                'user_type': self.user_profile.get('user_type'),
                'broker': self.user_profile.get('broker'),
                'exchanges': self.user_profile.get('exchanges', []),
                'products': self.user_profile.get('products', []),
                'order_types': self.user_profile.get('order_types', [])
            }
            
        except requests.exceptions.RequestException as e:
            # Parse Kite API error response if available
            error_details = self._parse_api_error_response(e.response if hasattr(e, 'response') else None)
            raise NetworkError(
                f"Network error during token generation: {error_details or str(e)}",
                context={'original_error': str(e), 'error_type': type(e).__name__}
            ) from e
    
    def invalidate_session(self) -> bool:
        """Invalidate current session.
        
        Returns:
            True if session invalidated successfully
            
        Raises:
            AuthenticationError: If invalidation fails
        """
        if not self.access_token:
            return True
        
        try:
            headers = {'Authorization': f'token {self.api_key}:{self.access_token}'}
            response = self.session.delete(
                f"{self.config.base_url}/session/token",
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            # Clear session data
            self.access_token = None
            self.session_expiry = None
            self.user_profile = None
            
            return True
            
        except requests.exceptions.RequestException as e:
            # Parse API error response for better error details
            error_details = self._parse_api_error_response(e.response if hasattr(e, 'response') else None)
            raise AuthenticationError(
                f"Failed to invalidate session: {error_details or str(e)}",
                context={'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None}
            ) from e
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid.
        
        Returns:
            True if session is valid and not expired
        """
        if not self.access_token:
            return False
        
        if self.session_expiry and datetime.now() >= self.session_expiry:
            return False
        
        return True    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (alias for is_session_valid).
        
        Returns:
            True if authenticated
        """
        return self.is_session_valid()    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information.
        
        Returns:
            Session info if available, None otherwise
        """
        if not self.is_session_valid():
            return None
        
        return {
            'access_token': self.access_token,
            'session_expiry': self.session_expiry.isoformat() if self.session_expiry else None,
            'user_profile': self.user_profile
        }    
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile information.
        
        Returns:
            User profile dict
            
        Raises:
            AuthenticationError: If not authenticated
        """
        if not self.is_authenticated():
            raise AuthenticationError("Access token required for profile retrieval")
        
        if self.user_profile:
            return self.user_profile
        
        # Make API call to get profile
        try:
            response = self._make_request('GET', '/user/profile')
            self.user_profile = response.get('data', {})
            return self.user_profile
        except (AuthenticationError, SessionExpiredError, InvalidCredentialsError, APIError, NetworkError):
            # Let authentication-related exceptions pass through
            raise
        except Exception as e:
            raise AuthenticationError(f"Failed to get profile: {str(e)}")    
    def refresh_session(self, request_token: str) -> Dict[str, str]:
        """Refresh session with new request token.
        
        Args:
            request_token: New request token
            
        Returns:
            New session data
        """
        # Invalidate current session
        try:
            self.invalidate_session()
        except AuthenticationError:
            pass  # Ignore errors during invalidation
        
        # Generate new session
        return self.generate_session(request_token)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.
        
        Returns:
            Headers dictionary with authorization
            
        Raises:
            AuthenticationError: If no valid session available
        """
        if not self.is_session_valid():
            raise AuthenticationError("No valid session available")
        
        return {
            'Authorization': f'token {self.api_key}:{self.access_token}',
            'X-Kite-Version': '3'
        }
    
    def refresh_access_token(self) -> str:
        """Refresh access token (requires refresh token).
        
        Returns:
            New access token
            
        Raises:
            NotImplementedError: Refresh token flow not yet implemented
        """
        # Note: Kite Connect doesn't support refresh tokens in the traditional sense
        # This would need to be implemented based on actual Kite API capabilities
        raise NotImplementedError("Refresh token flow not supported by Kite Connect API")
    
    def logout(self) -> bool:
        """Logout and invalidate current session.
        
        Returns:
            True if logout successful
        """
        try:
            self.invalidate_session()
            self.access_token = None  # Clear the access token
            self.user_profile = None  # Clear cached profile
            return True
        except Exception:
            return False
    
    def validate_session(self) -> bool:
        """Validate current session (alias for is_session_valid).
        
        Returns:
            True if session is valid
        """
        return self.is_session_valid()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data dict
            
        Raises:
            AuthenticationError: If authentication fails
            NetworkError: If network request fails
            APIError: If API returns error
        """
        if not self.access_token:
            raise AuthenticationError("Access token required for API requests")
        
        url = f"{self.config.base_url}{endpoint}"
        headers = self.get_auth_headers()
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            
            # Check status code and response data first
            if response.status_code >= 400:
                try:
                    data = response.json()
                except:
                    data = {}
                
                error_type = data.get('error_type', 'GeneralException')
                message = data.get('message', f'HTTP {response.status_code} Error')
                
                if response.status_code == 401:
                    raise AuthenticationError(message)
                elif response.status_code == 403:
                    raise SessionExpiredError(message)
                elif response.status_code == 400:
                    raise InvalidCredentialsError(message)
                else:
                    raise APIError(f"{error_type}: {message}")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'error':
                error_type = data.get('error_type', 'GeneralException')
                message = data.get('message', 'Unknown error')
                raise APIError(f"{error_type}: {message}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network request failed: {str(e)}") from e
        except Exception as e:
            if isinstance(e, (AuthenticationError, NetworkError, APIError, SessionExpiredError, InvalidCredentialsError)):
                raise
            raise APIError(f"Request failed: {str(e)}") from e
    
    def _parse_api_error_response(self, response) -> Optional[str]:
        """Parse Kite API error response to extract detailed error information.
        
        Args:
            response: HTTP response object
            
        Returns:
            Detailed error message or None if parsing fails
        """
        if not response:
            return None
        
        try:
            # Check if response has JSON content
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                
                # Extract Kite API error details
                if error_data.get('status') == 'error':
                    error_type = error_data.get('error_type', 'UnknownError')
                    message = error_data.get('message', 'No error message provided')
                    
                    # Include additional context if available
                    context_parts = [f"{error_type}: {message}"]
                    
                    if 'data' in error_data and error_data['data']:
                        context_parts.append(f"Details: {error_data['data']}")
                    
                    return " | ".join(context_parts)
            
            # Fallback to status code and reason
            return f"HTTP {response.status_code}: {response.reason}"
            
        except Exception:
            # If parsing fails, return basic info
            return f"HTTP {getattr(response, 'status_code', 'Unknown')} Error"