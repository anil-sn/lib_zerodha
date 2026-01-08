"""Unit tests for KiteFO."""

import pytest
from unittest.mock import Mock
import requests
import pandas as pd
from lib_zerodha.derivatives.kite_fo import KiteFO

class TestKiteFO:
    @pytest.fixture
    def mock_session(self):
        return Mock(spec=requests.Session)

    @pytest.fixture
    def fo(self, mock_session):
        return KiteFO(
            session=mock_session,
            get_auth_headers=lambda: {"Authorization": "token key:token"}
        )

    def test_get_fo_instruments(self, fo, mock_session):
        mock_response = Mock()
        mock_response.status_code = 200
        # CSV content
        mock_response.content = b"instrument_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n1,NIFTY24JAN21000CE,NIFTY,100,2024-01-25,21000,0.05,50,CE,NFO,NFO"
        mock_session.get.return_value = mock_response
        
        df = fo.get_fo_instruments("NFO")
        assert len(df) == 1
        assert df.iloc[0]['tradingsymbol'] == "NIFTY24JAN21000CE"

    def test_get_expiry_dates(self, fo, mock_session):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"instrument_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n1,NIFTY24JAN21000CE,NIFTY,100,2024-01-25,21000,0.05,50,CE,NFO,NFO\n2,NIFTY24FEB21000CE,NIFTY,200,2024-02-29,21000,0.05,50,CE,NFO,NFO"
        mock_session.get.return_value = mock_response
        
        dates = fo.get_expiry_dates("NIFTY")
        assert len(dates) == 2
        assert dates[0].month == 1
        assert dates[1].month == 2