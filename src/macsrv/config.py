"""Configuration management for macsrv."""

from dataclasses import dataclass, field
import configparser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    CONFIG_SECTION,
    DEFAULT_AUTO_STOP_TIME,
    DEFAULT_DISPLAY_SLEEP,
    DEFAULT_LOGGING,
)


@dataclass
class MacSrvConfig:
    """Application configuration backed by config.ini."""

    auto_stop_time: str = DEFAULT_AUTO_STOP_TIME
    display_sleep: int = DEFAULT_DISPLAY_SLEEP
    logging: bool = DEFAULT_LOGGING

    # ── Display metadata ──────────────────────────────────────────────────

    _DISPLAY_NAMES: Dict[str, str] = field(
        default_factory=lambda: {
            "auto_stop_time": "Auto Stop Time",
            "display_sleep": "Display Sleep (min)",
            "logging": "Logging",
        },
        repr=False,
    )

    _VALID_KEYS: List[str] = field(
        default_factory=lambda: ["auto_stop_time", "display_sleep", "logging"],
        repr=False,
    )

    _KEY_ALIASES: Dict[str, str] = field(
        default_factory=lambda: {
            "auto_stop": "auto_stop_time",
            "stop": "auto_stop_time",
            "auto-stop": "auto_stop_time",
            "display": "display_sleep",
        },
        repr=False,
    )

    @classmethod
    def load(cls) -> "MacSrvConfig":
        """Load configuration from disk, falling back to defaults."""
        cfg = cls()
        if not CONFIG_FILE.exists():
            return cfg

        parser = configparser.ConfigParser()
        parser.read(CONFIG_FILE)

        if not parser.has_section(CONFIG_SECTION):
            return cfg

        section = parser[CONFIG_SECTION]

        if "auto_stop_time" in section:
            cfg.auto_stop_time = section["auto_stop_time"]
        if "display_sleep" in section:
            try:
                cfg.display_sleep = int(section["display_sleep"])
            except (ValueError, TypeError):
                pass
        if "logging" in section:
            cfg.logging = section.getboolean("logging")

        return cfg

    def save(self) -> None:
        """Persist configuration to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        parser = configparser.ConfigParser()
        if CONFIG_FILE.exists():
            parser.read(CONFIG_FILE)

        if not parser.has_section(CONFIG_SECTION):
            parser.add_section(CONFIG_SECTION)

        parser[CONFIG_SECTION]["auto_stop_time"] = self.auto_stop_time
        parser[CONFIG_SECTION]["display_sleep"] = str(self.display_sleep)
        parser[CONFIG_SECTION]["logging"] = str(self.logging).lower()

        with open(CONFIG_FILE, "w") as f:
            parser.write(f)

    def set(self, key: str, value: str) -> Tuple[bool, str]:
        """Set a config key to a new value.

        Args:
            key: Config key name (case-insensitive, hyphen/underscore tolerant).
            value: New value as a string.

        Returns:
            Tuple of (success, error_message).
        """
        normalized = key.lower().replace("-", "_")

        # Resolve alias
        if normalized in self._KEY_ALIASES:
            normalized = self._KEY_ALIASES[normalized]

        if normalized not in self._VALID_KEYS:
            valid = ", ".join(self._VALID_KEYS)
            return False, f"Unknown key: {key!r}. Valid keys: {valid}"

        if normalized == "auto_stop_time":
            # Basic validation: HH:MM format
            parts = value.split(":")
            if len(parts) != 2:
                return False, "Invalid time format. Use HH:MM (e.g. 03:00)."
            try:
                h, m = int(parts[0]), int(parts[1])
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
            except ValueError:
                return False, "Time out of range. Use HH:MM (00:00-23:59)."
            self.auto_stop_time = value

        elif normalized == "display_sleep":
            try:
                val = int(value)
                if val < 0:
                    return False, "Display sleep must be a non-negative integer."
                self.display_sleep = val
            except ValueError:
                return False, "Display sleep must be an integer (minutes)."

        elif normalized == "logging":
            low = value.lower()
            if low not in ("true", "false", "1", "0", "yes", "no"):
                return False, "Logging must be true or false."
            self.logging = low in ("true", "1", "yes")

        self.save()
        return True, ""

    def display(self) -> Dict[str, str]:
        """Return a dict of display names to values for ``macsrv config``."""
        return {
            "auto_stop_time": self.auto_stop_time,
            "display_sleep": str(self.display_sleep),
            "logging": str(self.logging).lower(),
        }