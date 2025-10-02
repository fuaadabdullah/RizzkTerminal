"""Database helpers backed by SQLAlchemy."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_ENGINE: Engine | None = None


def _dsn() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return "sqlite:///" + str((data_dir / "rizzk.db").resolve())


def _engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(_dsn(), future=True)
    return _ENGINE


def init() -> None:
    """Ensure required tables exist."""
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    body TEXT NOT NULL
                )
                """
            )
        )


def add_journal(ts: int, body: str) -> int:
    """Persist a journal entry and return its identifier."""
    engine = _engine()
    with Session(engine) as session, session.begin():
        if engine.dialect.name == "sqlite":
            result = session.execute(
                text("INSERT INTO journal(ts, body) VALUES (:ts, :body)"),
                {"ts": ts, "body": body},
            )
            inserted_id = result.lastrowid
        else:
            result = session.execute(
                text("INSERT INTO journal(ts, body) VALUES (:ts, :body) RETURNING id"),
                {"ts": ts, "body": body},
            )
            inserted_id = result.scalar_one()
    return int(inserted_id or 0)


def list_journal(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent journal entries."""
    engine = _engine()
    with Session(engine) as session:
        rows = session.execute(
            text("SELECT id, ts, body FROM journal ORDER BY id DESC LIMIT :n"),
            {"n": limit},
        ).mappings()
        return [dict(row) for row in rows]
