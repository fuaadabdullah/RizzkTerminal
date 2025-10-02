"""Feature flag helpers for runtime toggles."""

from __future__ import annotations

import os

_ON_VALUES = {"1", "true", "yes", "y", "on"}


def flag(name: str, default: str = "0") -> bool:
    """Return True when the environment variable resolves to an on-value."""
    return (os.getenv(name, default) or "").strip().lower() in _ON_VALUES


AI_ENABLED = flag("AI_ENABLED", "0")
NEWS_ENABLED = flag("NEWS_ENABLED", "1")
SCREENER_ENABLED = flag("SCREENER_ENABLED", "1")
BACKTEST_ENABLED = flag("BACKTEST_ENABLED", "1")
