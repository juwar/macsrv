"""Package constants."""

from pathlib import Path
import platform
import sys

VERSION = "1.0.0"
APP_NAME = "macsrv"
APP_DISPLAY_NAME = "Mac Server CLI"

# ── XDG Base Directories ──────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / APP_NAME
STATE_DIR = Path.home() / ".local" / "state" / APP_NAME
CACHE_DIR = Path.home() / ".cache" / APP_NAME

# ── Files ─────────────────────────────────────────────────────────────────

CONFIG_FILE = CONFIG_DIR / "config.ini"
PID_FILE = STATE_DIR / "pid"
STARTED_AT_FILE = STATE_DIR / "started_at"
EXPIRES_AT_FILE = STATE_DIR / "expires_at"
LOGFILE = STATE_DIR / "logfile"

# ── Config defaults ───────────────────────────────────────────────────────

CONFIG_SECTION = "macsrv"
DEFAULT_AUTO_STOP_TIME = "02:00"
DEFAULT_DISPLAY_SLEEP = 10
DEFAULT_LOGGING = True

# ── macOS info ────────────────────────────────────────────────────────────

MACOS_VERSION = platform.mac_ver()[0]
IS_MACOS = sys.platform == "darwin"

# ── Exit codes ────────────────────────────────────────────────────────────

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_ALREADY_RUNNING = 2
EXIT_NOT_RUNNING = 3