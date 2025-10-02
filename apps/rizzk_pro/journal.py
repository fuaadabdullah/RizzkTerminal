"""SQLite-backed trade journaling helpers."""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd

from scripts.db_init import init_db

DB_PATH = Path(os.getenv("RIZZK_DB_PATH", "data/rizzk.db"))
EXPORTS_DIR = Path(os.getenv("RIZZK_EXPORTS", "obsidian/90_exports"))


def _connect() -> sqlite3.Connection:
    """Return a SQLite connection with basic pragmas applied."""

    init_db(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_dirs() -> None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_trades(limit: int | None = None) -> pd.DataFrame:
    """Return the most recent trades as a DataFrame."""

    with _connect() as conn:
        query = "SELECT * FROM trades ORDER BY date DESC, ROWID DESC"
        if limit:
            query += " LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(limit,))
        else:
            df = pd.read_sql_query(query, conn)
    return df


def _coerce_numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def save_trade(payload: Dict[str, Any]) -> tuple[str, Path]:
    """Insert or update a trade and emit a markdown export."""

    ensure_dirs()
    trade: Dict[str, Any] = dict(payload)
    trade_id = trade.get("id") or str(uuid.uuid4())
    trade["id"] = trade_id

    risk = _coerce_numeric(trade.get("risk")) or 0.0
    reward = _coerce_numeric(trade.get("reward")) or 0.0
    qty = _coerce_numeric(trade.get("qty")) or 0.0
    entry = _coerce_numeric(trade.get("entry"))
    exit_price = _coerce_numeric(trade.get("exit"))
    stop = _coerce_numeric(trade.get("stop"))

    if not trade.get("date"):
        trade["date"] = datetime.utcnow().strftime("%Y-%m-%d")

    if not trade.get("side"):
        trade["side"] = "long"

    if trade.get("tags") and isinstance(trade["tags"], Iterable) and not isinstance(trade["tags"], str):
        trade["tags"] = ",".join(str(t) for t in trade["tags"] if t)

    if risk <= 0 and qty and entry is not None and stop is not None:
        risk = abs(entry - stop) * qty
        trade["risk"] = risk

    if reward <= 0 and qty and entry is not None and exit_price is not None:
        reward = abs(exit_price - entry) * qty
        trade["reward"] = reward

    if risk <= 0:
        trade["rr"] = None
    else:
        trade["rr"] = (reward / risk) if reward else 0.0

    columns = [
        "id",
        "date",
        "ticker",
        "side",
        "entry",
        "exit",
        "stop",
        "qty",
        "risk",
        "reward",
        "rr",
        "thesis",
        "notes",
        "tags",
    ]
    values = [trade.get(col) for col in columns]

    placeholders = ",".join(["?"] * len(columns))
    insert_sql = f"INSERT OR REPLACE INTO trades ({','.join(columns)}) VALUES ({placeholders})"

    with _connect() as conn:
        conn.execute(insert_sql, values)
        conn.commit()

    export_name = f"trade_{trade['date']}_{trade.get('ticker','')}_{trade_id[:6]}".replace(" ", "_")
    export_path = EXPORTS_DIR / f"{export_name}.md"

    rr_value = trade.get("rr")
    risk_str = f"{risk:.2f}" if risk else "0.00"
    reward_str = f"{reward:.2f}" if reward else "0.00"
    rr_str = f"{rr_value:.2f}" if isinstance(rr_value, (int, float)) else ""

    md = [
        f"# Trade {trade_id}",
        f"- Date: {trade['date']}",
        f"- Ticker: {trade.get('ticker', '')}",
        f"- Side: {trade.get('side', '')}",
        f"- Entry: {entry if entry is not None else ''}",
        f"- Exit: {exit_price if exit_price is not None else ''}",
        f"- Stop: {stop if stop is not None else ''}",
        f"- Quantity: {qty}",
        f"- Risk ($): {risk_str}",
        f"- Reward ($): {reward_str}",
        f"- R:R: {rr_str}",
        f"- Thesis: {trade.get('thesis', '')}",
        f"- Notes: {trade.get('notes', '')}",
        f"- Tags: {trade.get('tags', '')}",
    ]
    export_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    return trade_id, export_path


__all__ = ["DB_PATH", "EXPORTS_DIR", "ensure_dirs", "fetch_trades", "save_trade"]
