"""Portfolio management for Kite Connect API."""

from typing import Dict, List, Optional, Union, Any
import requests
from datetime import datetime

from ..exceptions import APIError, NetworkError, ValidationError
from ..models.portfolio import Position, Holding, Portfolio


class KitePortfolio:
    """Handles portfolio management including positions and holdings."""
    
    def __init__(self, session: requests.Session, get_auth_headers: callable, config: Any):
        """Initialize portfolio management.
        
        Args:
            session: Requests session for API calls
            get_auth_headers: Function to get authentication headers
            config: Configuration object
        """
        self.session = session
        self.get_auth_headers = get_auth_headers
        self.config = config
    
    def get_positions(self) -> Dict[str, List[Position]]:
        """Get current positions.
        
        Returns:
            Dictionary with 'net' and 'day' positions
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{self.config.base_url}/portfolio/positions",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch positions'),
                    result.get('error_type')
                )
            
            data = result.get('data', {})
            positions = {
                'net': [Position.from_dict(pos) for pos in data.get('net', [])],
                'day': [Position.from_dict(pos) for pos in data.get('day', [])]
            }
            
            return positions
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching positions: {str(e)}")
    
    def get_holdings(self) -> List[Holding]:
        """Get long-term holdings.
        
        Returns:
            List of Holding objects
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        try:
            response = self.session.get(
                f"{self.config.base_url}/portfolio/holdings",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch holdings'),
                    result.get('error_type')
                )
            
            holdings_data = result.get('data', [])
            holdings = [Holding.from_dict(holding) for holding in holdings_data]
            
            return holdings
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching holdings: {str(e)}")
    
    def convert_position(self,
                        tradingsymbol: str,
                        exchange: str,
                        transaction_type: str,
                        position_type: str,
                        quantity: int,
                        old_product: str,
                        new_product: str) -> bool:
        """Convert position from one product type to another.
        
        Args:
            tradingsymbol: Trading symbol
            exchange: Exchange
            transaction_type: BUY or SELL
            position_type: day or overnight
            quantity: Quantity to convert
            old_product: Current product type (MIS, CNC, NRML)
            new_product: Target product type
            
        Returns:
            True if conversion successful
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If conversion fails
            NetworkError: If network request fails
        """
        # Validate parameters
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        valid_products = ['MIS', 'CNC', 'NRML']
        if old_product not in valid_products or new_product not in valid_products:
            raise ValidationError(f"Product types must be one of: {valid_products}")
        
        if old_product == new_product:
            raise ValidationError("Old and new product types cannot be the same")
        
        conversion_data = {
            'tradingsymbol': tradingsymbol,
            'exchange': exchange,
            'transaction_type': transaction_type.upper(),
            'position_type': position_type.lower(),
            'quantity': quantity,
            'old_product': old_product.upper(),
            'new_product': new_product.upper()
        }
        
        try:
            response = self.session.put(
                f"{self.config.base_url}/portfolio/positions",
                headers=self.get_auth_headers(),
                data=conversion_data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Position conversion failed'),
                    result.get('error_type')
                )
            
            return True
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error during position conversion: {str(e)}")
    
    def get_margins(self, segment: Optional[str] = None) -> Dict[str, Any]:
        """Get account margins.
        
        Args:
            segment: Optional segment (equity or commodity)
            
        Returns:
            Dictionary with margin details
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        url = f"{self.config.base_url}/user/margins"
        if segment:
            url += f"/{segment}"
            
        try:
            response = self.session.get(
                url,
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(
                    result.get('message', 'Failed to fetch margins'),
                    result.get('error_type')
                )
                
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error while fetching margins: {str(e)}")

    def get_portfolio_summary(self) -> Portfolio:
        """Get comprehensive portfolio summary.
        
        Returns:
            Portfolio object with positions, holdings, and summary
            
        Raises:
            APIError: If API request fails
            NetworkError: If network request fails
        """
        positions = self.get_positions()
        holdings = self.get_holdings()
        
        # Calculate portfolio metrics
        total_pnl = 0.0
        total_investment = 0.0
        
        # Calculate from positions
        for pos in positions['net']:
            total_pnl += pos.pnl
            total_investment += abs(pos.buy_value - pos.sell_value)
        
        # Calculate from holdings
        for holding in holdings:
            total_pnl += holding.pnl
            total_investment += holding.average_price * holding.quantity
        
        portfolio = Portfolio(
            positions=positions,
            holdings=holdings,
            total_pnl=total_pnl,
            total_investment=total_investment,
            last_updated=datetime.now()
        )
        
        return portfolio