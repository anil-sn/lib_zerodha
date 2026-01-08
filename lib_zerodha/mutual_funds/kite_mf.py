"""Mutual Funds trading and management."""

from typing import Dict, List, Optional, Union, Any
import requests
import json
import pandas as pd
from datetime import datetime

from ..exceptions import APIError, NetworkError, ValidationError, OrderError
from ..models.mutual_funds import MFOrder, MFSIP, MFHolding


class KiteMF:
    """Handles Mutual Fund orders, SIPs, and holdings."""
    
    def __init__(self, session: requests.Session, get_auth_headers: callable, config: Any):
        """Initialize Mutual Funds handler.
        
        Args:
            session: Requests session for API calls
            get_auth_headers: Function to get authentication headers
            config: Configuration object
        """
        self.session = session
        self.get_auth_headers = get_auth_headers
        self.config = config

    def get_orders(self, order_id: Optional[str] = None) -> Union[List[MFOrder], MFOrder]:
        """Get all MF orders or a specific order.
        
        Args:
            order_id: Specific order ID to fetch
            
        Returns:
            List of MFOrder or single MFOrder
        """
        try:
            url = f"{self.config.base_url}/mf/orders"
            if order_id:
                url += f"/{order_id}"
                
            response = self.session.get(
                url,
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(result.get('message', 'Failed to fetch MF orders'))
            
            data = result.get('data', [])
            
            if order_id:
                return MFOrder.from_dict(data)
            
            return [MFOrder.from_dict(order) for order in data]
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error fetching MF orders: {str(e)}")

    def place_order(self,
                   tradingsymbol: str,
                   transaction_type: str,
                   amount: Optional[float] = None,
                   quantity: Optional[float] = None,
                   tag: Optional[str] = None,
                   isin: Optional[str] = None) -> str:
        """Place a Mutual Fund order.
        
        Args:
            tradingsymbol: Fund trading symbol
            transaction_type: BUY or SELL
            amount: Amount to invest (for BUY)
            quantity: Quantity to redeem (for SELL)
            tag: Optional tag
            isin: ISIN (optional, if tradingsymbol not known)
            
        Returns:
            Order ID
        """
        if transaction_type.upper() == 'BUY' and not amount:
            raise ValidationError("Amount is required for BUY orders")
        if transaction_type.upper() == 'SELL' and not quantity:
            raise ValidationError("Quantity is required for SELL orders")
            
        payload = {
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type.upper(),
        }
        
        if amount:
            payload["amount"] = amount
        if quantity:
            payload["quantity"] = quantity
        if tag:
            payload["tag"] = tag
        if isin:
            payload["isin"] = isin
            
        try:
            response = self.session.post(
                f"{self.config.base_url}/mf/orders",
                headers=self.get_auth_headers(),
                data=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(result.get('message', 'MF order placement failed'))
                
            return result.get('data', {}).get('order_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error placing MF order: {str(e)}")

    def cancel_order(self, order_id: str) -> str:
        """Cancel a Mutual Fund order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Order ID
        """
        try:
            response = self.session.delete(
                f"{self.config.base_url}/mf/orders/{order_id}",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(result.get('message', 'MF order cancellation failed'))
                
            return result.get('data', {}).get('order_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error canceling MF order: {str(e)}")

    def get_sips(self, sip_id: Optional[str] = None) -> Union[List[MFSIP], MFSIP]:
        """Get all SIPs or a specific SIP.
        
        Args:
            sip_id: Specific SIP ID
            
        Returns:
            List of MFSIP or single MFSIP
        """
        try:
            url = f"{self.config.base_url}/mf/sips"
            if sip_id:
                url += f"/{sip_id}"
                
            response = self.session.get(
                url,
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(result.get('message', 'Failed to fetch SIPs'))
            
            data = result.get('data', [])
            
            if sip_id:
                return MFSIP.from_dict(data)
                
            return [MFSIP.from_dict(sip) for sip in data]
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error fetching SIPs: {str(e)}")

    def place_sip(self,
                 tradingsymbol: str,
                 amount: float,
                 instalments: int,
                 frequency: str,
                 instalment_day: Optional[int] = None,
                 initial_amount: Optional[float] = None,
                 tag: Optional[str] = None) -> str:
        """Place a new SIP.
        
        Args:
            tradingsymbol: Fund trading symbol
            amount: Instalment amount
            instalments: Total instalments (-1 for infinite)
            frequency: weekly, monthly, quarterly
            instalment_day: Day of month (for monthly)
            initial_amount: Amount for first instalment (optional)
            tag: Optional tag
            
        Returns:
            SIP ID
        """
        payload = {
            "tradingsymbol": tradingsymbol,
            "amount": amount,
            "instalments": instalments,
            "frequency": frequency.lower()
        }
        
        if instalment_day:
            payload["instalment_day"] = instalment_day
        if initial_amount:
            payload["initial_amount"] = initial_amount
        if tag:
            payload["tag"] = tag
            
        try:
            response = self.session.post(
                f"{self.config.base_url}/mf/sips",
                headers=self.get_auth_headers(),
                data=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(result.get('message', 'SIP placement failed'))
                
            return result.get('data', {}).get('sip_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error placing SIP: {str(e)}")

    def modify_sip(self,
                  sip_id: str,
                  amount: Optional[float] = None,
                  status: Optional[str] = None,
                  instalments: Optional[int] = None,
                  frequency: Optional[str] = None,
                  instalment_day: Optional[int] = None) -> str:
        """Modify an active SIP.
        
        Args:
            sip_id: SIP ID
            amount: New amount
            status: ACTIVE or PAUSED
            instalments: New instalment count
            frequency: New frequency
            instalment_day: New instalment day
            
        Returns:
            SIP ID
        """
        payload = {}
        if amount: payload["amount"] = amount
        if status: payload["status"] = status
        if instalments: payload["instalments"] = instalments
        if frequency: payload["frequency"] = frequency
        if instalment_day: payload["instalment_day"] = instalment_day
        
        if not payload:
            raise ValidationError("Nothing to modify")
            
        try:
            response = self.session.put(
                f"{self.config.base_url}/mf/sips/{sip_id}",
                headers=self.get_auth_headers(),
                data=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(result.get('message', 'SIP modification failed'))
                
            return result.get('data', {}).get('sip_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error modifying SIP: {str(e)}")

    def cancel_sip(self, sip_id: str) -> str:
        """Cancel a SIP.
        
        Args:
            sip_id: SIP ID to cancel
            
        Returns:
            SIP ID
        """
        try:
            response = self.session.delete(
                f"{self.config.base_url}/mf/sips/{sip_id}",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise OrderError(result.get('message', 'SIP cancellation failed'))
                
            return result.get('data', {}).get('sip_id')
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error canceling SIP: {str(e)}")

    def get_holdings(self) -> List[MFHolding]:
        """Get Mutual Fund holdings.
        
        Returns:
            List of MFHolding
        """
        try:
            response = self.session.get(
                f"{self.config.base_url}/mf/holdings",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'error':
                raise APIError(result.get('message', 'Failed to fetch MF holdings'))
            
            data = result.get('data', [])
            return [MFHolding.from_dict(holding) for holding in data]
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error fetching MF holdings: {str(e)}")

    def get_instruments(self) -> pd.DataFrame:
        """Get list of Mutual Funds instruments.
        
        Returns:
            DataFrame with MF instruments
        """
        try:
            response = self.session.get(
                f"{self.config.base_url}/mf/instruments",
                headers=self.get_auth_headers(),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            import io
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            return df
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error fetching MF instruments: {str(e)}")
