"""Portfolio models for positions and holdings."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import Instrument


@dataclass
class Position:
    """Trading position data."""
    tradingsymbol: str
    exchange: str
    instrument_token: int
    product: str
    quantity: int
    overnight_quantity: int
    multiplier: float
    average_price: float
    close_price: float
    last_price: float
    value: float
    pnl: float
    m2m: float  # Mark to market
    unrealised: float
    realised: float
    buy_quantity: int
    buy_price: float
    buy_value: float
    buy_m2m: float
    sell_quantity: int
    sell_price: float
    sell_value: float
    sell_m2m: float
    day_buy_quantity: int
    day_buy_price: float
    day_buy_value: float
    day_sell_quantity: int
    day_sell_price: float
    day_sell_value: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create Position from API response with resilient parsing."""
        from dataclasses import fields
        
        # Filter known fields to handle future API additions gracefully
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)
    
    @property
    def net_quantity(self) -> int:
        """Calculate net position quantity."""
        return self.buy_quantity - self.sell_quantity
    
    @property
    def pnl_percent(self) -> float:
        """Calculate P&L percentage."""
        if self.value == 0:
            return 0.0
        return (self.pnl / abs(self.value)) * 100
    
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.net_quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.net_quantity < 0
    
    @property
    def is_intraday(self) -> bool:
        """Check if position is intraday."""
        return self.product in ['MIS', 'CO']


@dataclass
class Holding:
    """Long-term holding data."""
    tradingsymbol: str
    exchange: str
    instrument_token: int
    isin: str
    product: str
    quantity: int
    t1_quantity: int  # T+1 quantity
    realised_quantity: int
    authorised_quantity: int
    authorised_date: Optional[datetime] = None
    opening_quantity: int = 0
    collateral_quantity: int = 0
    collateral_type: Optional[str] = None
    discrepancy: bool = False
    average_price: float = 0.0
    last_price: float = 0.0
    close_price: float = 0.0
    pnl: float = 0.0
    day_change: float = 0.0
    day_change_percentage: float = 0.0
    
    # Missing field from ISSUES_REPORT.md
    used_quantity: int = 0
    price: float = 0.0  # Additional field from API
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Holding':
        """Create Holding from API response with resilient parsing."""
        from dataclasses import fields
        from datetime import datetime
        
        # Parse authorised_date safely
        authorised_date = data.get('authorised_date')
        if isinstance(authorised_date, str):
            try:
                authorised_date = datetime.fromisoformat(authorised_date.replace(' ', 'T'))
            except ValueError:
                authorised_date = None
        
        # Filter known fields to handle future API additions gracefully
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        # Override with processed data
        filtered_data['authorised_date'] = authorised_date
        
        return cls(**filtered_data)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.authorised_date, str):
            try:
                self.authorised_date = datetime.fromisoformat(self.authorised_date.replace(' ', 'T'))
            except ValueError:
                self.authorised_date = None
    
    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        return self.quantity * self.last_price
    
    @property
    def investment_value(self) -> float:
        """Calculate total investment value."""
        return self.quantity * self.average_price
    
    @property
    def pnl_percent(self) -> float:
        """Calculate P&L percentage."""
        if self.average_price == 0:
            return 0.0
        return ((self.last_price - self.average_price) / self.average_price) * 100
    
    @property
    def available_quantity(self) -> int:
        """Get available quantity for trading."""
        return self.quantity - self.collateral_quantity


@dataclass
class MarginInfo:
    """Margin information."""
    available: Dict[str, float]
    utilised: Dict[str, float]
    net: float
    
    @property
    def total_available(self) -> float:
        """Get total available margin."""
        return sum(self.available.values())
    
    @property
    def total_utilised(self) -> float:
        """Get total utilised margin."""
        return sum(self.utilised.values())
    
    @property
    def utilisation_percent(self) -> float:
        """Calculate margin utilisation percentage."""
        total_available = self.total_available
        if total_available == 0:
            return 0.0
        return (self.total_utilised / total_available) * 100


@dataclass
class Portfolio:
    """Complete portfolio summary."""
    positions: Dict[str, List[Position]]
    holdings: List[Holding]
    total_pnl: float
    total_investment: float
    last_updated: datetime
    margin_info: Optional[MarginInfo] = None
    
    @property
    def net_positions(self) -> List[Position]:
        """Get net positions."""
        return self.positions.get('net', [])
    
    @property
    def day_positions(self) -> List[Position]:
        """Get day positions."""
        return self.positions.get('day', [])
    
    @property
    def total_holdings_value(self) -> float:
        """Calculate total holdings market value."""
        return sum(holding.market_value for holding in self.holdings)
    
    @property
    def total_positions_pnl(self) -> float:
        """Calculate total positions P&L."""
        total = 0.0
        for positions in self.positions.values():
            total += sum(pos.pnl for pos in positions)
        return total
    
    @property
    def total_holdings_pnl(self) -> float:
        """Calculate total holdings P&L."""
        return sum(holding.pnl for holding in self.holdings)
    
    @property
    def overall_pnl_percent(self) -> float:
        """Calculate overall P&L percentage."""
        if self.total_investment == 0:
            return 0.0
        return (self.total_pnl / self.total_investment) * 100
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get position summary statistics."""
        net_positions = self.net_positions
        
        if not net_positions:
            return {
                'total_positions': 0,
                'profitable_positions': 0,
                'loss_positions': 0,
                'win_rate': 0.0
            }
        
        profitable = sum(1 for pos in net_positions if pos.pnl > 0)
        loss_making = sum(1 for pos in net_positions if pos.pnl < 0)
        
        return {
            'total_positions': len(net_positions),
            'profitable_positions': profitable,
            'loss_positions': loss_making,
            'win_rate': (profitable / len(net_positions)) * 100 if net_positions else 0.0,
            'average_pnl': sum(pos.pnl for pos in net_positions) / len(net_positions)
        }