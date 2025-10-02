"""Miscellaneous helpers used across the app."""

from __future__ import annotations

from datetime import UTC, datetime


def humanize_timestamp(ts: int) -> str:
    """Return a human readable timestamp string in UTC."""
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
