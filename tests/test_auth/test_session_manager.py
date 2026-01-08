"""Unit tests for SessionManager."""

import pytest
import os
from unittest.mock import Mock, patch
from lib_zerodha.auth.session_manager import SessionManager
from lib_zerodha.auth.kite_auth import KiteAuth

class TestSessionManager:
    @pytest.fixture
    def auth(self):
        auth = Mock(spec=KiteAuth)
        auth.api_key = "test_api_key"
        auth.access_token = None
        auth.session_expiry = None
        auth.user_profile = None
        return auth

    def test_init(self, auth, tmp_path):
        session_file = str(tmp_path / "session.enc")
        sm = SessionManager(api_key="test_api_key", auth_instance=auth, session_file=session_file)
        assert sm.session_file == session_file

    def test_save_and_load_session(self, auth, tmp_path):
        session_file = str(tmp_path / "session.enc")
        sm = SessionManager(api_key="test_api_key", auth_instance=auth, session_file=session_file)
        
        # Setup auth data
        auth.access_token = "secret_token"
        auth.user_profile = {"user_id": "AB1234"}
        auth.is_session_valid.return_value = True
        
        # Save
        assert sm._save_session()
        assert os.path.exists(session_file)
        
        # Clear auth state
        auth.access_token = None
        auth.user_profile = None
        
        # Load
        assert sm._load_session()
        assert auth.access_token == "secret_token"
        assert auth.user_profile == {"user_id": "AB1234"}

    def test_invalidate_session(self, auth, tmp_path):
        session_file = str(tmp_path / "session.enc")
        sm = SessionManager(api_key="test_api_key", auth_instance=auth, session_file=session_file)
        
        # Create file
        with open(session_file, 'wb') as f:
            f.write(b"data")
            
        assert sm.invalidate_session()
        assert not os.path.exists(session_file)
        auth.invalidate_session.assert_called_once()
