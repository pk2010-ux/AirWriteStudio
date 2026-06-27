"""
Small logging helpers for packaged builds.

Windowed PyInstaller apps do not have a visible console, so crashes that happen
inside camera/model startup otherwise look like the application simply exits.
"""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
from pathlib import Path


APP_LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AirWrite Studio"
APP_LOG_FILE = APP_LOG_DIR / "airwrite.log"
_CRASH_FILE = None


def setup_logging() -> Path:
    """Configure file logging and fatal-crash dumps."""
    global _CRASH_FILE
    APP_LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(APP_LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
        force=True,
    )

    try:
        _CRASH_FILE = open(APP_LOG_FILE, "a", encoding="utf-8")
        faulthandler.enable(file=_CRASH_FILE, all_threads=True)
    except OSError:
        logging.exception("Could not enable faulthandler")

    def log_unhandled(exc_type, exc_value, exc_traceback):
        logging.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = log_unhandled
    logging.info("AirWrite Studio starting")
    return APP_LOG_FILE
