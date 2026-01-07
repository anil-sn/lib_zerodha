"""Date and time utilities for lib_zerodha."""

import pytz
from datetime import datetime, date, time, timedelta
from typing import Optional, Union


# Indian timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC


def get_market_timezone() -> pytz.BaseTzInfo:
    """Get Indian market timezone (IST)."""
    return IST


def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def today_ist() -> date:
    """Get today's date in IST."""
    return now_ist().date()


def to_ist(dt: datetime) -> datetime:
    """Convert datetime to IST.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Datetime in IST
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = UTC.localize(dt)
    return dt.astimezone(IST)


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Datetime in UTC
    """
    if dt.tzinfo is None:
        # Assume IST if no timezone info
        dt = IST.localize(dt)
    return dt.astimezone(UTC)


def parse_kite_datetime(dt_str: str) -> datetime:
    """Parse Kite Connect datetime string.
    
    Args:
        dt_str: Datetime string from Kite API
        
    Returns:
        Parsed datetime in IST
    """
    # Common Kite datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S+05:30',
        '%Y-%m-%dT%H:%M:%S+0530',
        '%Y-%m-%d'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                dt = IST.localize(dt)
            return to_ist(dt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse datetime: {dt_str}")


def is_market_day(check_date: date) -> bool:
    """Check if given date is a market trading day.
    
    Args:
        check_date: Date to check
        
    Returns:
        True if market is open
    """
    # Weekend check
    if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Basic holiday check (extend as needed)
    holidays_2026 = [
        date(2026, 1, 26),  # Republic Day
        date(2026, 8, 15),  # Independence Day
        date(2026, 10, 2),  # Gandhi Jayanti
        # Add more holidays as needed
    ]
    
    return check_date not in holidays_2026


def is_market_open(check_time: Optional[datetime] = None) -> bool:
    """Check if market is currently open.
    
    Args:
        check_time: Time to check (default: current time)
        
    Returns:
        True if market is open
    """
    if check_time is None:
        check_time = now_ist()
    else:
        check_time = to_ist(check_time)
    
    # Check if it's a market day
    if not is_market_day(check_time.date()):
        return False
    
    # Check if within market hours
    market_open = time(9, 15)  # 9:15 AM
    market_close = time(15, 30)  # 3:30 PM
    current_time = check_time.time()
    
    return market_open <= current_time <= market_close