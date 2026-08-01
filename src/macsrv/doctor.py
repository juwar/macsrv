"""Doctor — system diagnostics for macsrv."""

import subprocess
import shutil
from typing import List, Tuple

from .constants import CONFIG_FILE, STATE_DIR


class Check:
    """A single diagnostic check result."""

    def __init__(self, name: str, passed: bool, hint: str = ""):
        self.name = name
        self.passed = passed
        self.hint = hint

    def __str__(self) -> str:
        icon = "✓" if self.passed else "✗"
        return f"  {icon}  {self.name}"


def run() -> int:
    """Run all diagnostic checks and print results.

    Returns:
        Exit code: 0 if all pass, 1 otherwise.
    """
    checks: List[Check] = []

    # 1. caffeinate
    checks.append(_check_caffeinate())

    # 2. SSH / Remote Login
    checks.append(_check_remote_login())

    # 3. Tailscale
    checks.append(_check_tailscale_installed())
    checks.append(_check_tailscale_connected())

    # 4. Config
    checks.append(_check_config())

    # 5. State directory
    checks.append(_check_state_dir())

    # 6. Current caffeinate process
    checks.append(_check_current_process())

    print()
    print("  macsrv Doctor")
    print("  ────────────────────────")
    print()

    all_pass = True
    for c in checks:
        print(str(c))
        if not c.passed:
            all_pass = False
            if c.hint:
                print(f"       └─ {c.hint}")

    print()
    if all_pass:
        print("  ✅  All checks passed.")
    else:
        print("  ⚠️   Some checks failed. See suggestions above.")
    print()

    return 0 if all_pass else 1


def _check_caffeinate() -> Check:
    path = shutil.which("caffeinate")
    if path:
        return Check("caffeinate exists", True, f"Found at {path}")
    return Check(
        "caffeinate exists",
        False,
        "Not found. caffeinate ships with macOS — ensure /usr/bin/caffeinate is present.",
    )


def _check_remote_login() -> Check:
    """Check if SSH Remote Login is enabled.

    Uses ``pgrep`` to check for active sshd process instead of
    ``systemsetup`` which requires root.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-q", "sshd"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Check("SSH (Remote Login) enabled", True)
        return Check(
            "SSH (Remote Login) enabled",
            False,
            "Run: sudo systemsetup -setremotelogin on",
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return Check(
            "SSH (Remote Login) enabled",
            False,
            "Run: sudo systemsetup -setremotelogin on",
        )


def _check_tailscale_installed() -> Check:
    path = shutil.which("tailscale")
    if path:
        return Check("Tailscale installed", True, f"Found at {path}")
    return Check(
        "Tailscale installed",
        False,
        "Install from https://tailscale.com/download",
    )


def _check_tailscale_connected() -> Check:
    try:
        result = subprocess.run(
            ["tailscale", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Check("Tailscale connected", True)
        return Check(
            "Tailscale connected",
            False,
            "Run: tailscale up",
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return Check(
            "Tailscale connected",
            False,
            "Tailscale not found or not connected.",
        )


def _check_config() -> Check:
    if CONFIG_FILE.exists():
        return Check("Config file exists", True, str(CONFIG_FILE))
    return Check(
        "Config file exists",
        False,
        f"Not found at {CONFIG_FILE}. Run: macsrv config",
    )


def _check_state_dir() -> Check:
    if STATE_DIR.exists():
        return Check("State directory exists", True, str(STATE_DIR))
    return Check(
        "State directory exists",
        False,
        f"Not found at {STATE_DIR}. Will be created on first start.",
    )


def _check_current_process() -> Check:
    from .server import is_running
    running, pid = is_running()
    if running:
        return Check("caffeinate process running", True, f"PID {pid}")
    return Check("caffeinate process running", False, "No active caffeinate process.")