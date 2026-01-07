"""Derivatives (F&O) models."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base import Instrument


@dataclass
class FOInstrument:
    """Futures and Options instrument."""
    # Required fields from base Instrument
    instrument_token: int
    exchange_token: int
    tradingsymbol: str
    name: str
    last_price: float
    tick_size: float
    lot_size: int
    instrument_type: str
    segment: str
    exchange: str
    # F&O specific fields with defaults
    underlying: str = ""
    expiry: Optional[date] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CE or PE
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.expiry, str):
            self.expiry = datetime.strptime(self.expiry, '%Y-%m-%d').date()
    
    @property
    def is_future(self) -> bool:
        """Check if instrument is future."""
        return self.instrument_type == "FUT"
    
    @property
    def is_call_option(self) -> bool:
        """Check if instrument is call option."""
        return self.instrument_type == "CE"
    
    @property
    def is_put_option(self) -> bool:
        """Check if instrument is put option."""
        return self.instrument_type == "PE"
    
    @property
    def moneyness(self) -> str:
        """Calculate option moneyness relative to spot price."""
        if not self.is_option or not hasattr(self, 'spot_price'):
            return "N/A"
        
        if self.is_call_option:
            if self.spot_price > self.strike:
                return "ITM"  # In the Money
            elif self.spot_price < self.strike:
                return "OTM"  # Out of the Money
        else:  # Put option
            if self.spot_price < self.strike:
                return "ITM"
            elif self.spot_price > self.strike:
                return "OTM"
        
        return "ATM"  # At the Money
    
    @property
    def days_to_expiry(self) -> int:
        """Calculate days to expiry."""
        if not self.expiry:
            return 0
        return (self.expiry - date.today()).days


@dataclass
class OptionData:
    """Option contract data with Greeks."""
    strike: float
    instrument_type: str  # CE or PE
    tradingsymbol: str
    instrument_token: int
    last_price: float
    volume: int
    oi: int  # Open Interest
    bid_price: float
    ask_price: float
    iv: float  # Implied Volatility
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: Optional[float] = None
    
    @property
    def bid_ask_spread(self) -> float:
        """Calculate bid-ask spread."""
        return self.ask_price - self.bid_price
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        return (self.bid_price + self.ask_price) / 2
    
    @property
    def is_call(self) -> bool:
        """Check if option is call."""
        return self.instrument_type == "CE"
    
    @property
    def is_put(self) -> bool:
        """Check if option is put."""
        return self.instrument_type == "PE"


@dataclass
class OptionChain:
    """Complete option chain data."""
    symbol: str
    expiry: date
    ce_options: List[OptionData]
    pe_options: List[OptionData]
    last_updated: datetime
    underlying_price: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.expiry, str):
            self.expiry = datetime.strptime(self.expiry, '%Y-%m-%d').date()
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated)
    
    @property
    def all_strikes(self) -> List[float]:
        """Get all unique strike prices."""
        strikes = set()
        for option in self.ce_options + self.pe_options:
            strikes.add(option.strike)
        return sorted(list(strikes))
    
    @property
    def atm_strike(self) -> float:
        """Find at-the-money strike."""
        if not self.underlying_price:
            return 0.0
        
        strikes = self.all_strikes
        return min(strikes, key=lambda x: abs(x - self.underlying_price))
    
    def get_option_by_strike(self, strike: float, option_type: str) -> Optional[OptionData]:
        """Get option by strike and type.
        
        Args:
            strike: Strike price
            option_type: 'CE' or 'PE'
            
        Returns:
            OptionData or None if not found
        """
        options = self.ce_options if option_type.upper() == 'CE' else self.pe_options
        
        for option in options:
            if option.strike == strike:
                return option
        
        return None
    
    def get_strikes_range(self, center_strike: float, count: int = 10) -> List[float]:
        """Get strikes around a center strike.
        
        Args:
            center_strike: Center strike price
            count: Number of strikes on each side
            
        Returns:
            List of strike prices
        """
        strikes = self.all_strikes
        
        try:
            center_index = strikes.index(center_strike)
        except ValueError:
            # If exact strike not found, find nearest
            center_index = min(range(len(strikes)), 
                             key=lambda i: abs(strikes[i] - center_strike))
        
        start_index = max(0, center_index - count)
        end_index = min(len(strikes), center_index + count + 1)
        
        return strikes[start_index:end_index]
    
    def calculate_pcr(self) -> Dict[str, float]:
        """Calculate Put-Call Ratio metrics.
        
        Returns:
            Dictionary with PCR by volume and OI
        """
        ce_volume = sum(opt.volume for opt in self.ce_options)
        pe_volume = sum(opt.volume for opt in self.pe_options)
        ce_oi = sum(opt.oi for opt in self.ce_options)
        pe_oi = sum(opt.oi for opt in self.pe_options)
        
        pcr_volume = pe_volume / ce_volume if ce_volume > 0 else 0
        pcr_oi = pe_oi / ce_oi if ce_oi > 0 else 0
        
        return {
            'pcr_volume': pcr_volume,
            'pcr_oi': pcr_oi,
            'ce_volume': ce_volume,
            'pe_volume': pe_volume,
            'ce_oi': ce_oi,
            'pe_oi': pe_oi
        }


@dataclass
class FuturesContract:
    """Futures contract data."""
    symbol: str
    expiry: date
    lot_size: int
    instrument_token: int
    tradingsymbol: str
    last_price: float
    volume: int
    oi: int
    underlying_price: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.expiry, str):
            self.expiry = datetime.strptime(self.expiry, '%Y-%m-%d').date()
    
    @property
    def days_to_expiry(self) -> int:
        """Calculate days to expiry."""
        return (self.expiry - date.today()).days
    
    @property
    def basis(self) -> float:
        """Calculate basis (futures price - spot price)."""
        if not self.underlying_price:
            return 0.0
        return self.last_price - self.underlying_price
    
    @property
    def basis_percent(self) -> float:
        """Calculate basis as percentage of spot price."""
        if not self.underlying_price or self.underlying_price == 0:
            return 0.0
        return (self.basis / self.underlying_price) * 100
    
    @property
    def contract_value(self) -> float:
        """Calculate contract value."""
        return self.last_price * self.lot_size