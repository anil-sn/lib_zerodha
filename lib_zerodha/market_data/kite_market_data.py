"""Market data and quotes for Kite Connect API."""

from typing import Dict, List, Optional, Union, Any
import requests
from datetime import datetime, date
import pandas as pd

from ..config import config
from ..exceptions import APIError, NetworkError, ValidationError
from ..models.market_data import Quote, OHLC, DepthItem


class KiteMarketData:
    """Handles market data, quotes, and historical data."""
    
    def __init__(self, session: requests.Session, get_auth_headers: callable):
        """Initialize market data handler.
        
        Args:
            session: Requests session for API calls
            get_auth_headers: Function to get authentication headers
        """
        self.session = session
        self.get_auth_headers = get_auth_headers
    
    def get_quote(self, instruments: Union[str, List[str]]) -> Dict[str, Quote]:
        """Get real-time quotes for instruments.
        
        Args:
            instruments: Single instrument or list of instruments (exchange:tradingsymbol)
            
        Returns:
            Dictionary mapping instruments to Quote objects
            
        Raises:
            ValidationError: If instrument format is invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        # Normalize to list
        if isinstance(instruments, str):
            instruments = [instruments]
        
        # Validate instrument format
        for instrument in instruments:
            if ':' not in instrument:
                raise ValidationError(f"Invalid instrument format: {instrument}. Use 'exchange:tradingsymbol'")
        
        # Prepare request
        params = {'i': instruments}
        
        try:
            response = self.session.get(
                f"{config.BASE_URL}/quote",
                headers=self.get_auth_headers(),
                params=params,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch quotes'),
                    result.get('error_type')
                )
            
            # Convert to Quote objects
            quotes = {}
            for instrument, data in result.get('data', {}).items():
                quotes[instrument] = Quote(**data)
            
            return quotes
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching quotes: {str(e)}")
    
    def get_ltp(self, instruments: Union[str, List[str]]) -> Dict[str, float]:
        """Get last traded price for instruments.
        
        Args:
            instruments: Single instrument or list of instruments
            
        Returns:
            Dictionary mapping instruments to LTP values
            
        Raises:
            ValidationError: If instrument format is invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        # Normalize to list
        if isinstance(instruments, str):
            instruments = [instruments]
        
        # Validate instrument format
        for instrument in instruments:
            if ':' not in instrument:
                raise ValidationError(f"Invalid instrument format: {instrument}. Use 'exchange:tradingsymbol'")
        
        # Prepare request
        params = {'i': instruments}
        
        try:
            response = self.session.get(
                f"{config.BASE_URL}/quote/ltp",
                headers=self.get_auth_headers(),
                params=params,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch LTP'),
                    result.get('error_type')
                )
            
            # Extract LTP values
            ltp_data = {}
            for instrument, data in result.get('data', {}).items():
                ltp_data[instrument] = data.get('last_price', 0.0)
            
            return ltp_data
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching LTP: {str(e)}")
    
    def get_ohlc(self, instruments: Union[str, List[str]]) -> Dict[str, OHLC]:
        """Get OHLC data for instruments.
        
        Args:
            instruments: Single instrument or list of instruments
            
        Returns:
            Dictionary mapping instruments to OHLC objects
            
        Raises:
            ValidationError: If instrument format is invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        # Normalize to list
        if isinstance(instruments, str):
            instruments = [instruments]
        
        # Validate instrument format
        for instrument in instruments:
            if ':' not in instrument:
                raise ValidationError(f"Invalid instrument format: {instrument}. Use 'exchange:tradingsymbol'")
        
        # Prepare request
        params = {'i': instruments}
        
        try:
            response = self.session.get(
                f"{config.BASE_URL}/quote/ohlc",
                headers=self.get_auth_headers(),
                params=params,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch OHLC'),
                    result.get('error_type')
                )
            
            # Convert to OHLC objects
            ohlc_data = {}
            for instrument, data in result.get('data', {}).items():
                ohlc_data[instrument] = OHLC(
                    open=data.get('ohlc', {}).get('open', 0.0),
                    high=data.get('ohlc', {}).get('high', 0.0),
                    low=data.get('ohlc', {}).get('low', 0.0),
                    close=data.get('ohlc', {}).get('close', 0.0)
                )
            
            return ohlc_data
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching OHLC: {str(e)}")
    
    def get_historical_data(self,
                           instrument_token: int,
                           from_date: Union[str, date, datetime],
                           to_date: Union[str, date, datetime],
                           interval: str = "day",
                           continuous: bool = False,
                           oi: bool = False) -> pd.DataFrame:
        """Get historical candle data.
        
        Args:
            instrument_token: Instrument token
            from_date: Start date
            to_date: End date
            interval: Candle interval (minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day)
            continuous: Get continuous data for futures
            oi: Include open interest data
            
        Returns:
            DataFrame with OHLCV data
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        # Validate interval
        valid_intervals = [
            "minute", "3minute", "5minute", "10minute", "15minute", 
            "30minute", "60minute", "day"
        ]
        if interval not in valid_intervals:
            raise ValidationError(f"Invalid interval: {interval}. Valid: {valid_intervals}")
        
        # Convert dates to strings
        if isinstance(from_date, (date, datetime)):
            from_date = from_date.strftime('%Y-%m-%d')
        if isinstance(to_date, (date, datetime)):
            to_date = to_date.strftime('%Y-%m-%d')
        
        # Prepare request parameters
        params = {
            'from': from_date,
            'to': to_date,
            'interval': interval
        }
        if continuous:
            params['continuous'] = '1'
        if oi:
            params['oi'] = '1'
        
        try:
            response = self.session.get(
                f"{config.BASE_URL}/instruments/historical/{instrument_token}/{interval}",
                headers=self.get_auth_headers(),
                params=params,
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch historical data'),
                    result.get('error_type')
                )
            
            # Convert to DataFrame
            candles = result.get('data', {}).get('candles', [])
            if not candles:
                return pd.DataFrame()
            
            columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            if oi:
                columns.append('oi')
            
            df = pd.DataFrame(candles, columns=columns)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching historical data: {str(e)}")
    
    def get_instruments(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """Get list of tradable instruments.
        
        Args:
            exchange: Specific exchange to fetch instruments for (optional)
            
        Returns:
            DataFrame with instrument details
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        url = f"{config.BASE_URL}/instruments"
        if exchange:
            url += f"/{exchange}"
        
        try:
            response = self.session.get(
                url,
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            # The instruments endpoint returns CSV data
            df = pd.read_csv(response.content.decode('utf-8').splitlines())
            return df
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching instruments: {str(e)}")
        except Exception as e:
            raise APIError(f"Failed to parse instruments data: {str(e)}")