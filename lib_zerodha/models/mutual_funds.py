"""Mutual Fund models for orders, SIPs, and holdings."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

@dataclass
class MFOrder:
    """Mutual Fund Order model."""
    order_id: str
    tradingsymbol: str
    exchange: str = "MF"
    transaction_type: str = "BUY"
    status: str = "OPEN"
    fund: Optional[str] = None
    purchase_type: Optional[str] = None
    variety: Optional[str] = None
    folio: Optional[str] = None
    order_timestamp: Optional[datetime] = None
    exchange_order_id: Optional[str] = None
    exchange_timestamp: Optional[datetime] = None
    amount: float = 0.0
    quantity: float = 0.0
    price: float = 0.0
    last_price: float = 0.0
    average_price: float = 0.0
    placed_by: Optional[str] = None
    status_message: Optional[str] = None
    tag: Optional[str] = None
    settlement_id: Optional[str] = None
    last_price_date: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MFOrder':
        """Create MFOrder from API response."""
        from dataclasses import fields
        
        # Parse timestamps
        for field_name in ['order_timestamp', 'exchange_timestamp', 'last_price_date']:
            val = data.get(field_name)
            if isinstance(val, str):
                try:
                    # Handle varying timestamp formats
                    if len(val) == 10:  # YYYY-MM-DD
                        data[field_name] = datetime.strptime(val, "%Y-%m-%d")
                    else:
                        data[field_name] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    data[field_name] = None
        
        # Filter known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)

@dataclass
class MFSIP:
    """Mutual Fund SIP model."""
    sip_id: str
    tradingsymbol: str
    fund: str
    status: str
    transaction_type: str
    frequency: str
    sip_type: str
    instalment_amount: float
    instalments: int
    completed_instalments: int
    pending_instalments: int
    created: Optional[datetime] = None
    last_instalment: Optional[datetime] = None
    next_instalment: Optional[datetime] = None
    trigger_price: float = 0.0
    dividend_type: Optional[str] = None
    sip_reg_num: Optional[str] = None
    tag: Optional[str] = None
    instalment_day: Optional[int] = None
    step_up: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MFSIP':
        """Create MFSIP from API response."""
        from dataclasses import fields
        
        # Parse timestamps
        for field_name in ['created', 'last_instalment', 'next_instalment']:
            val = data.get(field_name)
            if isinstance(val, str):
                try:
                    if len(val) == 10:
                        data[field_name] = datetime.strptime(val, "%Y-%m-%d")
                    else:
                        data[field_name] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    data[field_name] = None
        
        # Filter known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)

@dataclass
class MFHolding:
    """Mutual Fund Holding model."""
    folio: str
    fund: str
    tradingsymbol: str
    average_price: float
    last_price: float
    pnl: float
    quantity: float
    last_price_date: Optional[datetime] = None
    pledged_quantity: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MFHolding':
        """Create MFHolding from API response."""
        from dataclasses import fields
        
        # Parse timestamps
        val = data.get('last_price_date')
        if isinstance(val, str):
            try:
                data['last_price_date'] = datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                data['last_price_date'] = None
        
        # Filter known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)
