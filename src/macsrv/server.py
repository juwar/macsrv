"""Server management — start/stop/restart caffeinate process."""

import os
import signal
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from .config import MacSrvConfig
from .constants import (
    PID_FILE,
    STARTED_AT_FILE,
    EXPIRES_AT_FILE,
    DISPLAY_SLEEP_SAVED_FILE,
    STATE_DIR,
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_ALREADY_RUNNING,
    EXIT_NOT_RUNNING,
)
from .logger import get_logger
from .utils import parse_time, parse_duration, seconds_until


class ServerError(Exception):
    """Raised on server operation failures."""


def _ensure_state_dir() -> None:
    """Create state directory if it doesn't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_pid_file() -> Optional[int]:
    """Read PID from state file, return None if missing or invalid."""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with *pid* is currently running.

    Uses ``kill -0`` which sends no signal but checks existence.
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _kill_all_caffeinate() -> None:
    """Kill all caffeinate processes owned by the current user.

    Prevents orphaned processes from a previous macsrv run that
    might still hold power assertions (e.g. PreventUserIdleDisplaySleep).
    """
    logger = get_logger()
    try:
        result = subprocess.run(
            ["pgrep", "-u", str(os.getuid()), "caffeinate"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return
        for pid_str in result.stdout.strip().splitlines():
            try:
                pid = int(pid_str)
                os.kill(pid, signal.SIGTERM)
                for _ in range(5):
                    if not _is_pid_alive(pid):
                        break
                    time.sleep(0.1)
                else:
                    os.kill(pid, signal.SIGKILL)
                logger.info("Killed stale caffeinate PID %d", pid)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
    except (subprocess.SubprocessError, FileNotFoundError):
        pass


def is_running() -> Tuple[bool, Optional[int]]:
    """Check if the server is currently running.

    Returns:
        Tuple of (running, pid). Automatically cleans up stale PID files.
    """
    pid = _read_pid_file()
    if pid is None:
        return False, None

    if _is_pid_alive(pid):
        return True, pid

    # Stale PID — clean up
    _restore_display_sleep()
    cleanup_state()
    return False, None


def get_expires_at() -> Optional[float]:
    """Read the expiration timestamp from state."""
    if not EXPIRES_AT_FILE.exists():
        return None
    try:
        return float(EXPIRES_AT_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def get_started_at() -> Optional[float]:
    """Read the started timestamp from state."""
    if not STARTED_AT_FILE.exists():
        return None
    try:
        return float(STARTED_AT_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def start(
    cfg: MacSrvConfig,
    until: Optional[str] = None,
    duration: Optional[str] = None,
) -> int:
    """Start the caffeinate server.

    Args:
        cfg: Current configuration.
        until: Optional override time (HH:MM).
        duration: Optional override duration (e.g. ``8h``, ``30m``).

    Returns:
        Exit code.
    """
    logger = get_logger()

    # Check if already running — offer restart
    running, pid = is_running()
    if running:
        logger.info("Server already running (PID %d).", pid)
        print("🟢 Mac Server is already running.")
        answer = input("Restart it? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return EXIT_ALREADY_RUNNING
        stop()

    # Calculate duration
    if duration:
        td = parse_duration(duration)
        seconds = int(td.total_seconds())
    elif until:
        target = parse_time(until)
        seconds = seconds_until(target)
    else:
        target = parse_time(cfg.auto_stop_time)
        seconds = seconds_until(target)

    if seconds <= 0:
        logger.error("Calculated duration is zero or negative.")
        print("❌ Target time is in the past. Nothing to do.")
        return EXIT_ERROR

    _ensure_state_dir()

    # Kill any stale caffeinate processes first
    _kill_all_caffeinate()

    # Set display sleep to 1 min for quick screen-off
    _set_display_sleep(1)

    # Force display to sleep immediately
    _force_display_sleep()

    # Start caffeinate
    # caffeinate -s keeps system awake on AC power but lets display sleep
    # normally. No -i/-d/-u: display follows normal sleep timeout.
    cmd = ["caffeinate", "-s", "-t", str(seconds)]
    logger.info("Starting: %s", " ".join(cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.error("caffeinate not found at /usr/bin/caffeinate")
        print("❌ caffeinate not found. Are you on macOS?")
        return EXIT_ERROR

    # Write state
    now = time.time()
    expires = now + seconds

    PID_FILE.write_text(str(proc.pid))
    STARTED_AT_FILE.write_text(str(int(now)))
    EXPIRES_AT_FILE.write_text(str(int(expires)))

    started_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
    expires_str = datetime.fromtimestamp(expires).strftime("%Y-%m-%d %H:%M:%S")

    logger.info(
        "Server started (PID %d, expires %s)",
        proc.pid,
        expires_str,
    )

    print(f"🚀 Mac Server started.")
    print(f"   PID       : {proc.pid}")
    print(f"   Expires   : {expires_str}")
    print(f"   Remaining : {_format_seconds(seconds)}")

    return EXIT_SUCCESS


def stop() -> int:
    """Stop the running server.

    Kills only the PID stored by this application.

    Returns:
        Exit code.
    """
    logger = get_logger()
    running, pid = is_running()

    if not running:
        print("💤 Mac Server is not running.")
        return EXIT_NOT_RUNNING

    try:
        os.kill(pid, signal.SIGTERM)
        # Give it a moment, then SIGKILL if still alive
        for _ in range(5):
            if not _is_pid_alive(pid):
                break
            time.sleep(0.1)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        logger.error("Permission denied killing PID %d", pid)
        print(f"❌ Permission denied killing PID {pid}. Try with sudo?")
        cleanup_state()
        return EXIT_ERROR

    logger.info("Server stopped (PID %d)", pid)
    print(f"💤 Mac Server stopped (PID {pid}).")
    _restore_display_sleep()
    cleanup_state()
    return EXIT_SUCCESS


def restart(cfg: MacSrvConfig) -> int:
    """Restart the server (stop then start).

    Args:
        cfg: Current configuration.

    Returns:
        Exit code.
    """
    stop()
    return start(cfg)


def cleanup_state() -> None:
    """Remove all state files."""
    for f in (PID_FILE, STARTED_AT_FILE, EXPIRES_AT_FILE, DISPLAY_SLEEP_SAVED_FILE):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


def _get_display_sleep() -> Optional[int]:
    """Read current display sleep timeout from pmset."""
    try:
        result = subprocess.run(
            ["pmset", "-g"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith("displaysleep"):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1])
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return None


def _set_display_sleep(minutes: int) -> None:
    """Set display sleep timeout.

    Tries sudo first (may prompt for password). If sudo is unavailable,
    falls back to forcing display sleep immediately.
    """
    logger = get_logger()

    # Only save if we haven't already saved
    if not DISPLAY_SLEEP_SAVED_FILE.exists():
        current = _get_display_sleep()
        if current is not None:
            DISPLAY_SLEEP_SAVED_FILE.write_text(str(current))
            logger.info("Saved display sleep value: %d min", current)

    # Try sudo -n first (non-interactive, uses cached credentials)
    for cmd in (
        ["sudo", "-n", "pmset", "-a", "displaysleep", str(minutes)],
        ["sudo", "pmset", "-a", "displaysleep", str(minutes)],
    ):
        try:
            result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Set display sleep to %d min", minutes)
                return
            # sudo -n fails with non-zero if no cached creds; try next
            if "-n" in cmd:
                continue
            logger.warning("sudo pmset failed: %s", result.stderr.strip())
        except subprocess.SubprocessError as e:
            if "-n" in cmd:
                continue
            logger.warning("Failed to set display sleep: %s", e)

    # If sudo failed, force display sleep now as best-effort
    logger.info("sudo unavailable — forcing display sleep immediately")
    _force_display_sleep()
    print("ℹ️  Run once to cache sudo: sudo pmset -a displaysleep 1")


def _restore_display_sleep() -> None:
    """Restore the original display sleep timeout."""
    logger = get_logger()
    if not DISPLAY_SLEEP_SAVED_FILE.exists():
        return
    try:
        original = int(DISPLAY_SLEEP_SAVED_FILE.read_text().strip())
        for cmd in (
            ["sudo", "-n", "pmset", "-a", "displaysleep", str(original)],
            ["sudo", "pmset", "-a", "displaysleep", str(original)],
        ):
            try:
                result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("Restored display sleep to %d min", original)
                    break
            except subprocess.SubprocessError:
                if "-n" in cmd:
                    continue
        DISPLAY_SLEEP_SAVED_FILE.unlink(missing_ok=True)
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        logger.warning("Failed to restore display sleep: %s", e)


def _force_display_sleep() -> None:
    """Force display to sleep immediately."""
    try:
        subprocess.run(
            ["pmset", "displaysleepnow"],
            timeout=5,
        )
    except subprocess.SubprocessError:
        pass


def _format_seconds(seconds: int) -> str:
    """Format seconds as human-readable."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if not h and s:
        parts.append(f"{s}s")
    if not parts:
        return "0s"
    return " ".join(parts)