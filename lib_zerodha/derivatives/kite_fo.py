"""Futures and Options (F&O) trading for Kite Connect API."""

from typing import Dict, List, Optional, Union, Any
import requests
from datetime import datetime, date
import pandas as pd

from ..config import config
from ..exceptions import APIError, NetworkError, ValidationError
from ..models.derivatives import FOInstrument, OptionChain, OptionData
from .option_chain import OptionChainAnalyzer
from .expiry_utils import ExpiryCalculator


class KiteFO:
    """Handles Futures and Options trading and data."""
    
    def __init__(self, session: requests.Session, get_auth_headers: callable):
        """Initialize F&O handler.
        
        Args:
            session: Requests session for API calls
            get_auth_headers: Function to get authentication headers
        """
        self.session = session
        self.get_auth_headers = get_auth_headers
        self.option_analyzer = OptionChainAnalyzer()
        self.expiry_calc = ExpiryCalculator()
    
    def get_fo_instruments(self, exchange: str = "NFO") -> pd.DataFrame:
        """Get F&O instruments list.
        
        Args:
            exchange: F&O exchange (NFO, BFO, CDS, MCX)
            
        Returns:
            DataFrame with F&O instrument details
            
        Raises:
            ValidationError: If exchange is invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        valid_exchanges = ['NFO', 'BFO', 'CDS', 'MCX']
        if exchange not in valid_exchanges:
            raise ValidationError(f"Invalid F&O exchange: {exchange}. Valid: {valid_exchanges}")
        
        try:
            response = self.session.get(
                f"{config.BASE_URL}/instruments/{exchange}",
                headers=self.get_auth_headers(),
                timeout=config.TIMEOUT
            )
            response.raise_for_status()
            
            # Parse CSV response
            df = pd.read_csv(response.content.decode('utf-8').splitlines())
            
            # Filter only F&O instruments
            fo_df = df[df['instrument_type'].isin(['FUT', 'CE', 'PE'])].copy()
            
            return fo_df
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching F&O instruments: {str(e)}")
        except Exception as e:
            raise APIError(f"Failed to parse F&O instruments data: {str(e)}")
    
    def get_option_chain(self,
                        symbol: str,
                        expiry: Optional[Union[str, date]] = None,
                        exchange: str = "NFO") -> OptionChain:
        """Get option chain for a symbol.
        
        Args:
            symbol: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
            expiry: Specific expiry date (optional, defaults to nearest)
            exchange: Exchange (NFO, BFO)
            
        Returns:
            OptionChain object with CE and PE data
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
            NetworkError: If network request fails
        """
        # Get F&O instruments
        instruments_df = self.get_fo_instruments(exchange)
        
        # Filter by symbol
        symbol_instruments = instruments_df[
            instruments_df['name'].str.contains(symbol, case=False, na=False)
        ]
        
        if symbol_instruments.empty:
            raise ValidationError(f"No F&O instruments found for symbol: {symbol}")
        
        # Get expiry date
        if expiry is None:
            expiry = self.expiry_calc.get_nearest_expiry(symbol_instruments)
        elif isinstance(expiry, str):
            expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
        
        # Filter by expiry
        expiry_str = expiry.strftime('%Y-%m-%d')
        expiry_instruments = symbol_instruments[
            symbol_instruments['expiry'] == expiry_str
        ]
        
        if expiry_instruments.empty:
            raise ValidationError(f"No instruments found for {symbol} expiry {expiry_str}")
        
        # Separate CE and PE options
        ce_options = expiry_instruments[expiry_instruments['instrument_type'] == 'CE']
        pe_options = expiry_instruments[expiry_instruments['instrument_type'] == 'PE']
        
        # Get quotes for all options
        ce_quotes = self._get_option_quotes(ce_options, exchange)
        pe_quotes = self._get_option_quotes(pe_options, exchange)
        
        # Build option chain
        option_chain = OptionChain(
            symbol=symbol,
            expiry=expiry,
            ce_options=ce_quotes,
            pe_options=pe_quotes,
            last_updated=datetime.now()
        )
        
        return option_chain
    
    def _get_option_quotes(self, instruments_df: pd.DataFrame, exchange: str) -> List[OptionData]:
        """Get quotes for option instruments.
        
        Args:
            instruments_df: DataFrame with instrument details
            exchange: Exchange name
            
        Returns:
            List of OptionData objects
        """
        option_data = []
        
        for _, instrument in instruments_df.iterrows():
            try:
                # Format instrument for quote API
                instrument_key = f"{exchange}:{instrument['tradingsymbol']}"
                
                # Get quote (you would call the market data module here)
                # For now, creating mock data structure
                option = OptionData(
                    strike=float(instrument['strike']),
                    instrument_type=instrument['instrument_type'],
                    tradingsymbol=instrument['tradingsymbol'],
                    instrument_token=int(instrument['instrument_token']),
                    last_price=0.0,  # Would be filled from quote
                    volume=0,
                    oi=0,
                    bid_price=0.0,
                    ask_price=0.0,
                    iv=0.0,  # Implied Volatility
                    delta=0.0,
                    gamma=0.0,
                    theta=0.0,
                    vega=0.0
                )
                
                option_data.append(option)
                
            except Exception:
                continue  # Skip instruments with errors
        
        return sorted(option_data, key=lambda x: x.strike)
    
    def get_expiry_dates(self, symbol: str, exchange: str = "NFO") -> List[date]:
        """Get available expiry dates for a symbol.
        
        Args:
            symbol: Underlying symbol
            exchange: Exchange (NFO, BFO)
            
        Returns:
            List of expiry dates sorted chronologically
            
        Raises:
            ValidationError: If symbol not found
            APIError: If API request fails
        """
        instruments_df = self.get_fo_instruments(exchange)
        
        # Filter by symbol
        symbol_instruments = instruments_df[
            instruments_df['name'].str.contains(symbol, case=False, na=False)
        ]
        
        if symbol_instruments.empty:
            raise ValidationError(f"No F&O instruments found for symbol: {symbol}")
        
        # Get unique expiry dates
        expiry_dates = symbol_instruments['expiry'].dropna().unique()
        
        # Convert to date objects and sort
        dates = []
        for expiry_str in expiry_dates:
            try:
                dates.append(datetime.strptime(expiry_str, '%Y-%m-%d').date())
            except ValueError:
                continue
        
        return sorted(dates)
    
    def get_strike_prices(self,
                         symbol: str,
                         expiry: Union[str, date],
                         option_type: Optional[str] = None,
                         exchange: str = "NFO") -> List[float]:
        """Get available strike prices for symbol and expiry.
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date
            option_type: CE, PE, or None for both
            exchange: Exchange (NFO, BFO)
            
        Returns:
            List of strike prices sorted numerically
            
        Raises:
            ValidationError: If parameters are invalid
        """
        instruments_df = self.get_fo_instruments(exchange)
        
        # Filter by symbol
        symbol_instruments = instruments_df[
            instruments_df['name'].str.contains(symbol, case=False, na=False)
        ]
        
        if symbol_instruments.empty:
            raise ValidationError(f"No F&O instruments found for symbol: {symbol}")
        
        # Convert expiry to string if needed
        if isinstance(expiry, date):
            expiry = expiry.strftime('%Y-%m-%d')
        
        # Filter by expiry
        expiry_instruments = symbol_instruments[
            symbol_instruments['expiry'] == expiry
        ]
        
        # Filter by option type if specified
        if option_type:
            expiry_instruments = expiry_instruments[
                expiry_instruments['instrument_type'] == option_type.upper()
            ]
        
        # Get unique strike prices
        strikes = expiry_instruments['strike'].dropna().unique()
        
        return sorted([float(strike) for strike in strikes])
    
    def calculate_option_greeks(self,
                               spot_price: float,
                               strike_price: float,
                               time_to_expiry: float,
                               risk_free_rate: float,
                               volatility: float,
                               option_type: str) -> Dict[str, float]:
        """Calculate option Greeks using Black-Scholes model.
        
        Args:
            spot_price: Current underlying price
            strike_price: Strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate
            volatility: Implied volatility
            option_type: 'CE' or 'PE'
            
        Returns:
            Dictionary with Greeks (delta, gamma, theta, vega, rho)
        """
        return self.option_analyzer.calculate_greeks(
            spot_price, strike_price, time_to_expiry,
            risk_free_rate, volatility, option_type
        )