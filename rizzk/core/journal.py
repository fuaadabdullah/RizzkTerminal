"""SQLite-backed trading journal."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "rizzk.db"


def _ensure_schema() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY,
                ts INTEGER NOT NULL,
                body TEXT NOT NULL
            )
            """
        )
        conn.commit()


_ensure_schema()


def add_entry(text: str) -> int:
    """Persist a new journal entry and return its row id."""
    body = (text or "").strip()
    if not body:
        raise ValueError("Journal entry cannot be empty.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO journal(ts, body) VALUES(?, ?)",
            (int(time.time()), body),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_entries(limit: int = 50) -> list[dict[str, Any]]:
    """Return the newest journal entries."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, ts, body FROM journal ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"id": int(row[0]), "ts": int(row[1]), "body": row[2]} for row in rows
    ]


def delete_entry(entry_id: int) -> None:
    """Remove a journal entry."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM journal WHERE id = ?", (int(entry_id),))
        conn.commit()
