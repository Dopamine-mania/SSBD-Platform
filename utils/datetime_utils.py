"""Date and time calculation utilities."""
from datetime import datetime, timedelta
import math

def round_up_to_interval(minutes: float, interval: int = 15) -> int:
    """Round up minutes to nearest interval.

    Args:
        minutes: Number of minutes to round
        interval: Interval to round to (default 15)

    Returns:
        Rounded minutes
    """
    return math.ceil(minutes / interval) * interval

def calculate_duration_minutes(start: datetime, end: datetime, pause_minutes: int = 0) -> float:
    """Calculate duration in minutes between two datetimes.

    Args:
        start: Start datetime
        end: End datetime
        pause_minutes: Minutes to subtract for pauses

    Returns:
        Duration in minutes
    """
    duration = (end - start).total_seconds() / 60
    return max(0, duration - pause_minutes)

def is_night_hour(dt: datetime, night_start: int = 22, night_end: int = 8) -> bool:
    """Check if datetime falls within night hours.

    Args:
        dt: Datetime to check
        night_start: Night period start hour (default 22)
        night_end: Night period end hour (default 8)

    Returns:
        True if in night period, False otherwise
    """
    hour = dt.hour
    return hour >= night_start or hour < night_end

def calculate_night_hours(start: datetime, end: datetime, night_start: int = 22, night_end: int = 8) -> float:
    """Calculate hours that fall within night period.

    Handles multi-day bookings correctly.

    Args:
        start: Start datetime
        end: End datetime
        night_start: Night period start hour (default 22)
        night_end: Night period end hour (default 8)

    Returns:
        Number of hours in night period
    """
    night_minutes = 0.0
    current = start

    while current < end:
        hour = current.hour

        if hour >= night_start or hour < night_end:
            # Calculate minutes in this hour that count as night
            next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            segment_end = min(next_hour, end)
            minutes = (segment_end - current).total_seconds() / 60
            night_minutes += minutes

        # Move to next hour
        current = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if current > end:
            break

    return night_minutes / 60

def check_time_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """Check if two time periods overlap.

    Args:
        start1: First period start
        end1: First period end
        start2: Second period start
        end2: Second period end

    Returns:
        True if periods overlap, False otherwise
    """
    return (start1 < end2) and (end1 > start2)
