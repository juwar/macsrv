"""Utility functions for time parsing and formatting."""

from datetime import datetime, timedelta
import re
from typing import Optional, Tuple


def parse_time(time_str: str) -> datetime:
    """Parse HH:MM into a datetime, returning today or tomorrow.

    If the parsed time is in the past, returns tomorrow's time instead.

    Args:
        time_str: Time in HH:MM format (24-hour).

    Returns:
        A datetime for today (or tomorrow if today's time has passed).
    """
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str.strip())
    if not m:
        raise ValueError(f"Invalid time format: {time_str!r} (expected HH:MM)")

    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time out of range: {time_str!r}")

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return target


def parse_duration(duration_str: str) -> timedelta:
    """Parse a human-readable duration string.

    Supported formats: ``8h``, ``30m``, ``30s``, ``2h30m``, ``90m``.

    Args:
        duration_str: Duration string like ``8h``, ``30m``, ``2h30m``.

    Returns:
        A timedelta.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    pattern = r"^(\d+h)?(\d+m)?(\d+s)?$"
    m = re.match(pattern, duration_str.strip().lower())
    if not m or (not m.group(1) and not m.group(2) and not m.group(3)):
        raise ValueError(
            f"Invalid duration: {duration_str!r} (use e.g. 8h, 30m, 30s, 2h30m)"
        )

    hours = int(m.group(1).rstrip("h")) if m.group(1) else 0
    minutes = int(m.group(2).rstrip("m")) if m.group(2) else 0
    seconds = int(m.group(3).rstrip("s")) if m.group(3) else 0

    if hours == 0 and minutes == 0 and seconds == 0:
        raise ValueError(f"Duration cannot be zero: {duration_str!r}")

    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def format_remaining(seconds: int) -> str:
    """Format seconds into a human-readable remaining time string.

    Args:
        seconds: Number of seconds remaining.

    Returns:
        A string like ``11h 42m`` or ``42m 30s``.
    """
    if seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not hours and secs:
        parts.append(f"{secs}s")
    if not parts:
        return "0s"
    return " ".join(parts)


def format_timestamp(ts: Optional[float]) -> str:
    """Format a Unix timestamp for display.

    Returns a friendly string like ``Today 14:22`` or ``2025-08-01 14:22``.

    Args:
        ts: Unix timestamp, or None.

    Returns:
        Formatted string, or ``-`` if ts is None.
    """
    if ts is None:
        return "-"
    dt = datetime.fromtimestamp(ts)
    now = datetime.now()
    if dt.date() == now.date():
        return f"Today {dt:%H:%M}"
    tomorrow = now.date() + timedelta(days=1)
    if dt.date() == tomorrow:
        return f"Tomorrow {dt:%H:%M}"
    return dt.strftime("%Y-%m-%d %H:%M")


def seconds_until(target: datetime) -> int:
    """Calculate seconds from now until *target*.

    Args:
        target: Future datetime.

    Returns:
        Number of seconds (guaranteed non-negative).
    """
    delta = (target - datetime.now()).total_seconds()
    return max(0, int(delta))