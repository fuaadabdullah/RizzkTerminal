"""Application logging configuration."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "rizzk.log"


def setup_logger() -> None:
    """Configure root logging with rotation and console output."""
    LOG_DIR.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(level)
    root.addHandler(handler)
    root.addHandler(logging.StreamHandler())
