"""Initialize the SQLite database that powers trade journaling."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(os.getenv("RIZZK_DB_PATH", "data/rizzk.db"))


def init_db(db_path: Path | str | None = None) -> Path:
    """Create the journal database and return its resolved path."""

    target = Path(db_path) if db_path else DEFAULT_DB
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target) as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS trades (
              id TEXT PRIMARY KEY,
              date TEXT NOT NULL,
              ticker TEXT NOT NULL,
              side TEXT CHECK(side IN ('long','short')) NOT NULL,
              entry REAL,
              exit REAL,
              stop REAL,
              qty REAL,
              risk REAL,
              reward REAL,
              rr REAL,
              thesis TEXT,
              notes TEXT,
              tags TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);
            CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
            """
        )

    return target.resolve()


def main() -> None:
    path = init_db()
    print(f"[db] ready: {path}")


if __name__ == "__main__":
    main()
