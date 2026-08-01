"""Status display for macsrv."""

from datetime import datetime
from typing import Optional

from .server import is_running, get_started_at, get_expires_at
from .utils import format_remaining, format_timestamp
from .constants import EXIT_SUCCESS, EXIT_NOT_RUNNING


def display_status() -> int:
    """Print a beautiful status report to stdout.

    Returns:
        Exit code.
    """
    running, pid = is_running()

    if not running:
        print()
        print("  Mac Server")
        print("  ────────────────────────")
        print("  Status")
        print("  🔴  Stopped")
        print()
        return EXIT_NOT_RUNNING

    started = get_started_at()
    expires = get_expires_at()
    remaining_seconds = int(expires - datetime.now().timestamp()) if expires else 0

    print()
    print("  Mac Server")
    print("  ────────────────────────")
    print()
    print("  Status")
    print("  🟢  Running")
    print()
    print(f"  Started   : {format_timestamp(started)}")
    print(f"  Expires   : {format_timestamp(expires)}")
    print(f"  Remaining : {format_remaining(remaining_seconds)}")
    print(f"  PID       : {pid}")
    print()
    print("  Power")
    print(f"  System    : {'Awake' if remaining_seconds > 0 else 'Allowed to Sleep'}")
    print(f"  Display   : {'Sleeps on schedule' if remaining_seconds > 0 else 'Allowed to Sleep'}")
    print()

    return EXIT_SUCCESS