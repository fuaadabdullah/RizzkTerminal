"""Background job to refresh cached market data for watchlist symbols."""

from __future__ import annotations

import argparse
import io
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "rizzk.db"
CACHE_DIR = DATA_DIR / "watchlist"
LOG = logging.getLogger("refresh")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def stooq_url(symbol: str, period: str = "1y") -> str:
    return f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def fetch_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    url = stooq_url(symbol, period)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    if df.empty:
        raise ValueError(f"stooq returned no rows for {symbol}")
    df.columns = [c.title() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
    df["Symbol"] = normalize_symbol(symbol)
    return df


def load_watchlist_symbols() -> list[str]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
        return [normalize_symbol(row[0]) for row in rows]
    finally:
        conn.close()


def refresh_symbols(symbols: Iterable[str]) -> None:
    for sym in symbols:
        try:
            df = fetch_history(sym)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Could not refresh %s: %s", sym, exc)
            continue
        target = CACHE_DIR / f"{sym}.csv"
        df.to_csv(target, index=False)
        LOG.info("Refreshed %s (%d rows)", sym, len(df))


def run_once() -> None:
    ensure_storage()
    symbols = load_watchlist_symbols()
    if not symbols:
        LOG.info("No watchlist symbols to refresh")
        return
    LOG.info("Refreshing %d watchlist symbols", len(symbols))
    refresh_symbols(symbols)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true", help="Run indefinitely")
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds to sleep between refresh cycles when looping",
    )
    args = parser.parse_args(argv)

    setup_logging()
    try:
        if not args.loop:
            run_once()
            return 0
        while True:
            start = datetime.utcnow()
            LOG.info(
                "Starting refresh cycle at %sZ", start.strftime("%Y-%m-%d %H:%M:%S")
            )
            run_once()
            LOG.info("Sleeping for %d seconds", args.interval)
            time.sleep(max(args.interval, 1))
    except KeyboardInterrupt:
        LOG.info("Received interrupt, stopping")
        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.exception("Refresh loop failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
