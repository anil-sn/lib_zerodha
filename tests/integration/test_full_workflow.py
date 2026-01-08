"""Integration tests for LibZerodha using MockKiteServer."""

import pytest
from datetime import date
from lib_zerodha import KiteClient, AuthenticationError

class TestFullWorkflow:
    """Simulates a complete trading session workflow."""

    def test_complete_session(self, test_config, tmp_path):
        # 1. Initialize Client
        session_file = str(tmp_path / "session_complete.enc")
        client = KiteClient(
            api_key=test_config.api_key,
            api_secret=test_config.api_secret,
            session_file=session_file
        )
        
        # 2. Login
        # MockKiteServer expects 'test_request_token' to be present
        session = client.generate_session(request_token="test_request_token")
        assert session["access_token"] == "valid_access_token"
        assert client.is_authenticated()
        
        # 3. Check Profile
        profile = client.get_profile()
        assert profile["user_id"] == "AB1234"
        assert profile["broker"] == "ZERODHA"
        
        # 4. Fetch Quotes
        quotes = client.get_quote(["NSE:INFY"])
        assert "NSE:INFY" in quotes
        assert quotes["NSE:INFY"].last_price == 1412.95
        
        # 5. Check Margins
        margins = client.get_margins()
        assert margins["equity"]["enabled"] is True
        assert margins["equity"]["available"]["cash"] == 245431.6
        
        # 6. Place Order
        order_id = client.place_order(
            variety="regular",
            exchange="NSE",
            tradingsymbol="INFY",
            transaction_type="BUY",
            quantity=10,
            product="MIS",
            order_type="LIMIT",
            price=1400.0
        )
        assert order_id.startswith("100") # Based on MockServer logic
        
        # 7. Check Order Book
        orders = client.get_orders()
        found_order = next((o for o in orders if o["order_id"] == order_id), None)
        assert found_order is not None
        assert found_order["tradingsymbol"] == "INFY"
        assert found_order["status"] == "OPEN"
        
        # 8. Modify Order
        mod_result = client.modify_order(
            order_id=order_id,
            variety="regular",
            quantity=20,
            price=1410.0
        )
        assert mod_result == order_id
        
        # Verify modification in order book
        orders = client.get_orders()
        updated_order = next((o for o in orders if o["order_id"] == order_id), None)
        assert updated_order["quantity"] == 20
        assert updated_order["price"] == 1410.0
        
        # 9. Cancel Order
        cancel_result = client.cancel_order(order_id=order_id, variety="regular")
        assert cancel_result == order_id
        
        # Verify cancellation
        orders = client.get_orders()
        cancelled_order = next((o for o in orders if o["order_id"] == order_id), None)
        assert cancelled_order["status"] == "CANCELLED"
        
        # 10. Portfolio (Positions & Holdings)
        positions = client.get_positions()
        assert "net" in positions
        assert len(positions["net"]) > 0
        assert positions["net"][0].tradingsymbol == "LEADMINI17DECFUT"
        
        holdings = client.get_holdings()
        assert len(holdings) > 0
        assert holdings[0].tradingsymbol == "AARON"

    def test_unauthenticated_access(self, test_config, tmp_path):
        """Verify that API calls fail without valid session."""
        session_file = str(tmp_path / "session_unauth.enc")
        client = KiteClient(api_key=test_config.api_key, session_file=session_file)
        
        with pytest.raises(AuthenticationError):
            client.get_profile()

    def test_invalid_login(self, test_config):
        """Verify login failure with wrong API key."""
        client = KiteClient(api_key="wrong_key", api_secret="wrong_secret")
        
        with pytest.raises(Exception): # NetworkError or AuthenticationError
            client.generate_session(request_token="any")
