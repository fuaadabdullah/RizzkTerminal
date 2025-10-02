"""Miscellaneous helpers used across the app."""

from __future__ import annotations

from datetime import datetime, timezone


def humanize_timestamp(ts: int) -> str:
    """Return a human readable timestamp string in UTC."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
