"""Advanced session management with auto-renewal and persistence."""

import json
import os
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path

from .kite_auth import KiteAuth
from ..exceptions import AuthenticationError
from ..config import config


class SessionManager:
    """Advanced session manager with persistence and auto-renewal."""
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None,
                 session_file: Optional[str] = None,
                 auto_refresh_callback: Optional[Callable[[], str]] = None):
        """Initialize session manager.
        
        Args:
            api_key: Kite Connect API key
            api_secret: API secret for token generation
            session_file: File path to persist session data
            auto_refresh_callback: Callback to get new request token for auto-refresh
        """
        self.auth = KiteAuth(api_key, api_secret)
        self.session_file = session_file or self._default_session_file()
        self.auto_refresh_callback = auto_refresh_callback
        
        # Load existing session if available
        self._load_session()
    
    def _default_session_file(self) -> str:
        """Get default session file path."""
        home = Path.home()
        lib_dir = home / '.lib_zerodha'
        lib_dir.mkdir(exist_ok=True)
        return str(lib_dir / 'session.json')
    
    def _load_session(self) -> bool:
        """Load session from file.
        
        Returns:
            True if session loaded successfully
        """
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                
                # Restore session data
                self.auth.access_token = data.get('access_token')
                self.auth.user_profile = data.get('user_profile')
                
                expiry_str = data.get('session_expiry')
                if expiry_str:
                    self.auth.session_expiry = datetime.fromisoformat(expiry_str)
                
                return True
        except Exception:
            pass  # Ignore errors, will create new session
        
        return False
    
    def _save_session(self) -> bool:
        """Save session to file.
        
        Returns:
            True if session saved successfully
        """
        try:
            if self.auth.access_token:
                data = {
                    'access_token': self.auth.access_token,
                    'user_profile': self.auth.user_profile,
                    'session_expiry': self.auth.session_expiry.isoformat() if self.auth.session_expiry else None,
                    'saved_at': datetime.now().isoformat()
                }
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
                
                with open(self.session_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                return True
        except Exception:
            pass  # Ignore errors
        
        return False
    
    def create_session(self, request_token: str) -> Dict[str, str]:
        """Create new session and persist it.
        
        Args:
            request_token: Request token from Kite login
            
        Returns:
            Session data
        """
        result = self.auth.generate_session(request_token)
        self._save_session()
        return result
    
    def get_valid_session(self) -> Optional[Dict[str, str]]:
        """Get valid session, auto-refreshing if needed.
        
        Returns:
            Valid session data or None
        """
        # Check if current session is valid
        if self.auth.is_session_valid():
            return self.auth.get_session_info()
        
        # Try auto-refresh if callback available
        if self.auto_refresh_callback:
            try:
                request_token = self.auto_refresh_callback()
                return self.create_session(request_token)
            except Exception:
                pass  # Auto-refresh failed
        
        return None
    
    def invalidate_session(self) -> bool:
        """Invalidate current session and remove from file.
        
        Returns:
            True if invalidated successfully
        """
        result = self.auth.invalidate_session()
        
        # Remove session file
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
        except Exception:
            pass  # Ignore errors
        
        return result
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers, auto-refreshing if needed.
        
        Returns:
            Authentication headers
            
        Raises:
            AuthenticationError: If no valid session can be obtained
        """
        session = self.get_valid_session()
        if not session:
            raise AuthenticationError("No valid session available and auto-refresh failed")
        
        return self.auth.get_auth_headers()
    
    def is_session_valid(self) -> bool:
        """Check if session is valid.
        
        Returns:
            True if session is valid
        """
        return self.auth.is_session_valid()
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get detailed session status.
        
        Returns:
            Session status information
        """
        session_info = self.auth.get_session_info()
        
        return {
            'is_valid': self.auth.is_session_valid(),
            'access_token': self.auth.access_token[:10] + '...' if self.auth.access_token else None,
            'session_expiry': session_info.get('session_expiry') if session_info else None,
            'user_id': self.auth.user_profile.get('user_id') if self.auth.user_profile else None,
            'user_name': self.auth.user_profile.get('user_name') if self.auth.user_profile else None,
            'broker': self.auth.user_profile.get('broker') if self.auth.user_profile else None,
            'session_file': self.session_file,
            'auto_refresh_enabled': self.auto_refresh_callback is not None
        }