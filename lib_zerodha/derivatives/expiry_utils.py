"""Expiry date utilities for derivatives."""

import calendar
from datetime import datetime, date, timedelta
from typing import List, Optional, Union
import pandas as pd


class ExpiryCalculator:
    """Calculate expiry dates for various derivative instruments.
    
    Allows injection of custom holiday calendars for accurate calculations.
    """
    
    # Default NSE holidays (fallback)
    DEFAULT_HOLIDAYS = [
        date(2026, 1, 26),  # Republic Day
        date(2026, 3, 14),  # Holi
        date(2026, 8, 15),  # Independence Day
        date(2026, 10, 2),  # Gandhi Jayanti
        # Add more holidays as needed
    ]
    
    def __init__(self, holidays: Optional[List[date]] = None):
        """Initialize ExpiryCalculator.
        
        Args:
            holidays: List of holiday dates. Defaults to 2026 list if None.
        """
        self.holidays = holidays if holidays is not None else self.DEFAULT_HOLIDAYS.copy()
        # Backward compatibility alias
        self.NSE_HOLIDAYS_2026 = self.holidays

    def set_holidays(self, holidays: List[date]):
        """Set the holiday calendar.
        
        Args:
            holidays: List of holiday dates
        """
        self.holidays = sorted(holidays)
        self.NSE_HOLIDAYS_2026 = self.holidays

    def add_holiday(self, holiday: Union[date, str]):
        """Add a single holiday to the calendar.
        
        Args:
            holiday: Date object or string 'YYYY-MM-DD'
        """
        if isinstance(holiday, str):
            holiday = datetime.strptime(holiday, '%Y-%m-%d').date()
        
        if holiday not in self.holidays:
            self.holidays.append(holiday)
            self.holidays.sort()
    
    def get_nearest_expiry(self, instruments_df: pd.DataFrame) -> date:
        """Get nearest expiry date from instruments DataFrame.
        
        Args:
            instruments_df: DataFrame with instrument data
            
        Returns:
            Nearest expiry date
        """
        if instruments_df.empty:
            raise ValueError("No instruments provided")
        
        today = date.today()
        expiry_dates = []
        
        for expiry_str in instruments_df['expiry'].dropna().unique():
            try:
                expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                if expiry_date >= today:
                    expiry_dates.append(expiry_date)
            except ValueError:
                continue
        
        if not expiry_dates:
            raise ValueError("No valid future expiry dates found")
        
        return min(expiry_dates)
    
    def get_monthly_expiry(self, year: int, month: int) -> date:
        """Get monthly expiry date (last Thursday of the month).
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Monthly expiry date
        """
        # Get last day of month
        last_day = calendar.monthrange(year, month)[1]
        last_date = date(year, month, last_day)
        
        # Find last Thursday
        # Thursday is weekday 3 (Monday is 0)
        while last_date.weekday() != 3:
            last_date -= timedelta(days=1)
        
        # Check if it's a holiday
        if last_date in self.holidays:
            # Move to previous trading day
            last_date -= timedelta(days=1)
            while last_date.weekday() >= 5 or last_date in self.holidays:
                last_date -= timedelta(days=1)
        
        return last_date
    
    def get_weekly_expiry(self, year: int, month: int, week: int) -> date:
        """Get weekly expiry date (Thursday of specific week).
        
        Args:
            year: Year
            month: Month
            week: Week number in month (1-4)
            
        Returns:
            Weekly expiry date
        """
        # Find first Thursday of the month
        first_day = date(year, month, 1)
        
        # Find first Thursday
        days_to_thursday = (3 - first_day.weekday()) % 7
        first_thursday = first_day + timedelta(days=days_to_thursday)
        
        # Calculate target Thursday
        target_thursday = first_thursday + timedelta(weeks=week-1)
        
        # Ensure it's still in the same month
        if target_thursday.month != month:
            raise ValueError(f"Week {week} Thursday is not in month {month}")
        
        # Check if it's a holiday
        if target_thursday in self.holidays:
            # Move to previous trading day
            target_thursday -= timedelta(days=1)
            while (target_thursday.weekday() >= 5 or 
                   target_thursday in self.holidays):
                target_thursday -= timedelta(days=1)
        
        return target_thursday
    
    def get_next_expiry_dates(self, symbol: str, count: int = 6) -> List[date]:
        """Get next N expiry dates for a symbol.
        
        Args:
            symbol: Symbol name (e.g., 'NIFTY', 'BANKNIFTY')
            count: Number of expiry dates to return
            
        Returns:
            List of next expiry dates
        """
        expiry_dates = []
        current_date = date.today()
        
        # Different symbols have different expiry patterns
        if symbol.upper() in ['NIFTY', 'BANKNIFTY']:
            # Weekly expiries
            current_month = current_date.month
            current_year = current_date.year
            
            for _ in range(count * 2):  # Generate more to filter
                try:
                    # Try each week of the month
                    for week in range(1, 6):  # Up to 5 weeks
                        try:
                            expiry = self.get_weekly_expiry(current_year, current_month, week)
                            if expiry > current_date and expiry not in expiry_dates:
                                expiry_dates.append(expiry)
                                if len(expiry_dates) >= count:
                                    return sorted(expiry_dates)
                        except ValueError:
                            continue
                    
                    # Move to next month
                    current_month += 1
                    if current_month > 12:
                        current_month = 1
                        current_year += 1
                        
                except Exception:
                    continue
        
        else:
            # Monthly expiries for stocks
            current_month = current_date.month
            current_year = current_date.year
            
            for _ in range(count):
                try:
                    expiry = self.get_monthly_expiry(current_year, current_month)
                    if expiry > current_date:
                        expiry_dates.append(expiry)
                    
                    current_month += 1
                    if current_month > 12:
                        current_month = 1
                        current_year += 1
                        
                except Exception:
                    continue
        
        return sorted(expiry_dates[:count])
    
    def is_expiry_day(self, check_date: date, symbol: Optional[str] = None) -> bool:
        """Check if given date is an expiry day.
        
        Args:
            check_date: Date to check
            symbol: Symbol to check (optional)
            
        Returns:
            True if it's an expiry day
        """
        # Thursday is expiry day
        if check_date.weekday() != 3:
            return False
        
        # Check if it's a holiday
        if check_date in self.holidays:
            return False
        
        return True
    
    def get_days_to_expiry(self, expiry_date: date) -> int:
        """Calculate days to expiry.
        
        Args:
            expiry_date: Expiry date
            
        Returns:
            Number of days to expiry
        """
        return (expiry_date - date.today()).days
    
    def get_time_to_expiry_years(self, expiry_date: date) -> float:
        """Calculate time to expiry in years (for options pricing).
        
        Args:
            expiry_date: Expiry date
            
        Returns:
            Time to expiry in years
        """
        days_to_expiry = self.get_days_to_expiry(expiry_date)
        return days_to_expiry / 365.25  # Account for leap years