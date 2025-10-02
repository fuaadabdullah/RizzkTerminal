"""Journal helpers built on top of the database layer."""

from __future__ import annotations

import time
from typing import Any

from . import db


def add_entry(text: str) -> int:
    """Store a journal entry and return its identifier."""
    body = (text or "").strip()
    if not body:
        raise ValueError("Cannot save an empty journal entry.")
    ts = int(time.time())
    return db.add_journal(ts=ts, body=body)


def list_entries(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent journal entries."""
    return db.list_journal(limit=limit)
