"""Simple test to verify pytest works."""

import pytest


class TestBasic:
    """Basic test to verify pytest infrastructure."""

    def test_simple_assertion(self):
        """Test that pytest can run simple assertions."""
        assert 1 + 1 == 2
        assert "hello" == "hello"
        
    def test_basic_imports(self):
        """Test that we can import the library."""
        from lib_zerodha import KiteClient
        assert KiteClient is not None
        
    def test_client_creation(self):
        """Test basic client creation."""
        from lib_zerodha import KiteClient
        
        client = KiteClient(api_key="test", api_secret="secret")
        assert client.api_key == "test"
