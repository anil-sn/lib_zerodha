"""Advanced session management with encryption and security."""

import json
import os
import fcntl
import stat
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .kite_auth import KiteAuth
from ..exceptions.api_exceptions import AuthenticationError, SessionExpiredError


class SessionManager:
    """Secure session manager with encryption and file locking."""
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None,
                 session_file: Optional[str] = None,
                 auto_refresh_callback: Optional[Callable[[], str]] = None,
                 encryption_password: Optional[str] = None,
                 auth_instance: Optional[KiteAuth] = None,
                 config: Any = None):
        """Initialize session manager.
        
        Args:
            api_key: Kite Connect API key
            api_secret: API secret for token generation
            session_file: File path to persist session data
            auto_refresh_callback: Callback to get new request token for auto-refresh
            encryption_password: Password for session encryption (defaults to api_key)
            auth_instance: Existing KiteAuth instance to use
            config: Configuration object
        """
        self.config = config
        self.auth = auth_instance or KiteAuth(api_key, api_secret, config=config)
        self.session_file = session_file or self._default_session_file()
        self.auto_refresh_callback = auto_refresh_callback
        
        # Setup encryption
        self.encryption_password = encryption_password or api_key
        # Cipher is created per operation with unique salt
        
        # Load existing session if available
        self._load_session()
    
    def _default_session_file(self) -> str:
        """Get default session file path with secure permissions."""
        home = Path.home()
        lib_dir = home / '.lib_zerodha'
        lib_dir.mkdir(mode=0o700, exist_ok=True)  # Secure directory permissions
        return str(lib_dir / 'session.enc')
    
    def _create_cipher(self, salt: bytes) -> Fernet:
        """Create encryption cipher from password and salt."""
        password = self.encryption_password.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)
    
    def _load_session(self) -> bool:
        """Load and decrypt session from file with file locking.
        
        Returns:
            True if session loaded successfully
        """
        if not os.path.exists(self.session_file):
            return False
        
        try:
            with open(self.session_file, 'rb') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                
                try:
                    # Read salt (first 16 bytes)
                    salt = f.read(16)
                    if len(salt) != 16:
                        return False
                        
                    encrypted_data = f.read()
                    if not encrypted_data:
                        return False
                    
                    # Create cipher with read salt
                    cipher = self._create_cipher(salt)
                    
                    # Decrypt session data
                    decrypted_data = cipher.decrypt(encrypted_data)
                    data = json.loads(decrypted_data.decode())
                    
                    # Check session expiry
                    expiry_str = data.get('session_expiry')
                    if expiry_str:
                        expiry = datetime.fromisoformat(expiry_str)
                        if datetime.now() > expiry:
                            # Session expired
                            return False
                        self.auth.session_expiry = expiry
                    
                    # Restore session data
                    self.auth.access_token = data.get('access_token')
                    self.auth.user_profile = data.get('user_profile')
                    
                    return True
                    
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except Exception:
            # Clear invalid session file if corrupted
            return False
    
    def _save_session(self) -> bool:
        """Save and encrypt session to file with file locking.
        
        Returns:
            True if session saved successfully
        """
        if not self.auth.access_token:
            return False
        
        try:
            # Prepare session data
            data = {
                'access_token': self.auth.access_token,
                'user_profile': self.auth.user_profile,
                'session_expiry': self.auth.session_expiry.isoformat() if self.auth.session_expiry else None,
                'saved_at': datetime.now().isoformat()
            }
            
            # Generate new random salt
            salt = os.urandom(16)
            cipher = self._create_cipher(salt)
            
            # Encrypt session data
            json_data = json.dumps(data, indent=2)
            encrypted_data = cipher.encrypt(json_data.encode())
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.session_file), mode=0o700, exist_ok=True)
            
            # Atomic write with file locking
            temp_file = self.session_file + '.tmp'
            with open(temp_file, 'wb') as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    f.write(salt) # Write salt first
                    f.write(encrypted_data)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Atomically replace the original file
            os.rename(temp_file, self.session_file)
            
            # Set secure file permissions
            os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
            
            return True
            
        except Exception:
            return False
    
    def create_session(self, request_token: str) -> Dict[str, str]:
        """Create new session and persist it securely.
        
        Args:
            request_token: Request token from Kite login
            
        Returns:
            Session data
        """
        result = self.auth.generate_session(request_token)
        
        # Set session expiry (6 AM next day)
        now = datetime.now()
        next_day_6am = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        self.auth.session_expiry = next_day_6am
        
        # Save encrypted session
        self._save_session()
            
        return result
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid."""
        return self.auth.is_session_valid()
    
    def invalidate_session(self) -> bool:
        """Invalidate current session and remove persistent data."""
        try:
            self.auth.invalidate_session()
            
            # Remove session file securely
            if os.path.exists(self.session_file):
                file_size = os.path.getsize(self.session_file)
                with open(self.session_file, 'wb') as f:
                    f.write(os.urandom(file_size))
                os.remove(self.session_file)
            
            return True
        except Exception:
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get auth headers, refreshing if necessary."""
        if not self.is_session_valid():
            if self.auto_refresh_callback:
                token = self.auto_refresh_callback()
                self.create_session(token)
            else:
                raise AuthenticationError("Session invalid and no refresh callback")
        
        return self.auth.get_auth_headers()
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get detailed session status."""
        return {
            'is_valid': self.is_session_valid(),
            'user_id': self.auth.user_profile.get('user_id') if self.auth.user_profile else None,
            'session_file': self.session_file,
            'auto_refresh_enabled': self.auto_refresh_callback is not None
        }
