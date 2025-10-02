"""Data-layer regression checks."""
from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import db_init  # noqa: E402


def test_db_init_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("RIZZK_DB_PATH", str(tmp_path / "rizzk.db"))
    path = db_init.init_db(tmp_path / "rizzk.db")
    assert path.exists()


def test_journal_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("RIZZK_DB_PATH", str(tmp_path / "rizzk.db"))
    exports_dir = tmp_path / "exports"
    monkeypatch.setenv("RIZZK_EXPORTS", str(exports_dir))

    journal = importlib.import_module("apps.rizzk_pro.journal")
    journal = importlib.reload(journal)

    trade_id, note_path = journal.save_trade(
        {
            "date": "2024-01-01",
            "ticker": "MSFT",
            "side": "long",
            "entry": 100.0,
            "stop": 95.0,
            "exit": 110.0,
            "qty": 10.0,
            "risk": 50.0,
            "reward": 100.0,
            "thesis": "Breakout",
            "notes": "CLI test",
            "tags": "test",
        }
    )

    assert note_path.exists()

    df = journal.fetch_trades()
    assert not df.empty
    assert trade_id in df["id"].values
    assert (df["rr"].fillna(0) >= 0).all()


def test_rr_nonnegative(tmp_path, monkeypatch):
    db_file = tmp_path / "rizzk.db"
    monkeypatch.setenv("RIZZK_DB_PATH", str(db_file))
    db_init.init_db(db_file)
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT COALESCE(rr, 0) FROM trades").fetchall()
    for (rr,) in rows:
        assert rr >= 0
