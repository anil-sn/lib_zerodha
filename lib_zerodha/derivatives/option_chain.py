"""Option chain analysis utilities."""

import math
from typing import Dict, List, Optional
from scipy.stats import norm
import numpy as np

from ..models.derivatives import OptionChain, OptionData


class OptionChainAnalyzer:
    """Analyzes option chain data and calculates Greeks."""
    
    def calculate_greeks(self,
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
        if time_to_expiry <= 0 or volatility <= 0:
            return {
                'delta': 0.0, 'gamma': 0.0, 'theta': 0.0,
                'vega': 0.0, 'rho': 0.0
            }
        
        # Black-Scholes calculations
        d1 = (math.log(spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / \
             (volatility * math.sqrt(time_to_expiry))
        
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        # Standard normal distribution
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        n_d1 = norm.pdf(d1)
        
        if option_type.upper() == 'CE':  # Call option
            delta = N_d1
            rho = strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * N_d2
        else:  # Put option
            delta = N_d1 - 1
            rho = -strike_price * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * (1 - N_d2)
        
        # Greeks (same for both call and put)
        gamma = n_d1 / (spot_price * volatility * math.sqrt(time_to_expiry))
        
        theta_part1 = -(spot_price * n_d1 * volatility) / (2 * math.sqrt(time_to_expiry))
        if option_type.upper() == 'CE':
            theta = (theta_part1 - risk_free_rate * strike_price * 
                    math.exp(-risk_free_rate * time_to_expiry) * N_d2) / 365
        else:
            theta = (theta_part1 + risk_free_rate * strike_price * 
                    math.exp(-risk_free_rate * time_to_expiry) * (1 - N_d2)) / 365
        
        vega = spot_price * math.sqrt(time_to_expiry) * n_d1 / 100
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'theta': round(theta, 4),
            'vega': round(vega, 4),
            'rho': round(rho / 100, 4)
        }
    
    def calculate_implied_volatility(self,
                                   option_price: float,
                                   spot_price: float,
                                   strike_price: float,
                                   time_to_expiry: float,
                                   risk_free_rate: float,
                                   option_type: str,
                                   max_iterations: int = 100,
                                   tolerance: float = 1e-6) -> float:
        """Calculate implied volatility using Newton-Raphson method.
        
        Args:
            option_price: Market price of the option
            spot_price: Current underlying price
            strike_price: Strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate
            option_type: 'CE' or 'PE'
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence tolerance
            
        Returns:
            Implied volatility
        """
        # Initial guess
        volatility = 0.2
        
        for _ in range(max_iterations):
            # Calculate theoretical price
            theoretical_price = self._black_scholes_price(
                spot_price, strike_price, time_to_expiry,
                risk_free_rate, volatility, option_type
            )
            
            # Calculate vega (price sensitivity to volatility)
            vega = self._calculate_vega(
                spot_price, strike_price, time_to_expiry,
                risk_free_rate, volatility
            )
            
            if abs(vega) < 1e-10:  # Avoid division by zero
                break
            
            # Newton-Raphson update
            price_diff = theoretical_price - option_price
            volatility_new = volatility - price_diff / vega
            
            if abs(volatility_new - volatility) < tolerance:
                return max(volatility_new, 0.001)  # Minimum vol of 0.1%
            
            volatility = max(volatility_new, 0.001)
        
        return volatility
    
    def _black_scholes_price(self,
                            spot_price: float,
                            strike_price: float,
                            time_to_expiry: float,
                            risk_free_rate: float,
                            volatility: float,
                            option_type: str) -> float:
        """Calculate Black-Scholes option price."""
        if time_to_expiry <= 0:
            if option_type.upper() == 'CE':
                return max(spot_price - strike_price, 0)
            else:
                return max(strike_price - spot_price, 0)
        
        d1 = (math.log(spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / \
             (volatility * math.sqrt(time_to_expiry))
        
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        
        if option_type.upper() == 'CE':  # Call option
            price = (spot_price * norm.cdf(d1) - 
                    strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
        else:  # Put option
            price = (strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - 
                    spot_price * norm.cdf(-d1))
        
        return max(price, 0)
    
    def _calculate_vega(self,
                       spot_price: float,
                       strike_price: float,
                       time_to_expiry: float,
                       risk_free_rate: float,
                       volatility: float) -> float:
        """Calculate vega (sensitivity to volatility)."""
        d1 = (math.log(spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / \
             (volatility * math.sqrt(time_to_expiry))
        
        return spot_price * math.sqrt(time_to_expiry) * norm.pdf(d1)
    
    def analyze_option_chain(self, option_chain: OptionChain) -> Dict[str, any]:
        """Analyze option chain for key metrics.
        
        Args:
            option_chain: OptionChain object
            
        Returns:
            Dictionary with analysis results
        """
        ce_options = option_chain.ce_options
        pe_options = option_chain.pe_options
        
        analysis = {
            'total_ce_oi': sum(opt.oi for opt in ce_options),
            'total_pe_oi': sum(opt.oi for opt in pe_options),
            'total_ce_volume': sum(opt.volume for opt in ce_options),
            'total_pe_volume': sum(opt.volume for opt in pe_options),
            'max_pain': self._calculate_max_pain(option_chain),
            'pcr_oi': 0.0,  # Put-Call Ratio by OI
            'pcr_volume': 0.0,  # Put-Call Ratio by Volume
            'support_levels': self._find_support_levels(pe_options),
            'resistance_levels': self._find_resistance_levels(ce_options)
        }
        
        # Calculate PCR ratios
        if analysis['total_ce_oi'] > 0:
            analysis['pcr_oi'] = analysis['total_pe_oi'] / analysis['total_ce_oi']
        
        if analysis['total_ce_volume'] > 0:
            analysis['pcr_volume'] = analysis['total_pe_volume'] / analysis['total_ce_volume']
        
        return analysis
    
    def _calculate_max_pain(self, option_chain: OptionChain) -> float:
        """Calculate max pain level."""
        all_strikes = set()
        
        # Collect all unique strikes
        for opt in option_chain.ce_options + option_chain.pe_options:
            all_strikes.add(opt.strike)
        
        max_pain_strike = 0
        min_total_pain = float('inf')
        
        for strike in all_strikes:
            total_pain = 0
            
            # Calculate pain for CE options
            for ce_opt in option_chain.ce_options:
                if strike > ce_opt.strike:
                    total_pain += (strike - ce_opt.strike) * ce_opt.oi
            
            # Calculate pain for PE options
            for pe_opt in option_chain.pe_options:
                if strike < pe_opt.strike:
                    total_pain += (pe_opt.strike - strike) * pe_opt.oi
            
            if total_pain < min_total_pain:
                min_total_pain = total_pain
                max_pain_strike = strike
        
        return max_pain_strike
    
    def _find_support_levels(self, pe_options: List[OptionData]) -> List[float]:
        """Find support levels based on PE open interest."""
        # Sort by OI in descending order
        sorted_options = sorted(pe_options, key=lambda x: x.oi, reverse=True)
        
        # Return top 3 strikes with highest PE OI
        return [opt.strike for opt in sorted_options[:3]]
    
    def _find_resistance_levels(self, ce_options: List[OptionData]) -> List[float]:
        """Find resistance levels based on CE open interest."""
        # Sort by OI in descending order
        sorted_options = sorted(ce_options, key=lambda x: x.oi, reverse=True)
        
        # Return top 3 strikes with highest CE OI
        return [opt.strike for opt in sorted_options[:3]]