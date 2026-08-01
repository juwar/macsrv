"""Logging setup for macsrv."""

import logging
import sys
from pathlib import Path
from typing import Optional

from .constants import LOGFILE, STATE_DIR


def setup_logging(logging_enabled: bool = True, logfile: Optional[Path] = None) -> logging.Logger:
    """Configure and return the application logger.

    Args:
        logging_enabled: If True, writes to both file and stderr.
        logfile: Path to log file. Defaults to LOGFILE constant.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("macsrv")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if logging_enabled:
        target = logfile or LOGFILE
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(target)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


def get_logger() -> logging.Logger:
    """Return the existing macsrv logger."""
    return logging.getLogger("macsrv")