"""Generate a daily operational note inside the Obsidian vault."""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple

from scripts.db_init import init_db

VAULT_ROOT = Path(os.getenv("RIZZK_VAULT", "obsidian"))
EXPORTS_DIR = Path(os.getenv("RIZZK_EXPORTS", VAULT_ROOT / "90_exports"))
OUT_DIR = VAULT_ROOT / "00_inbox"
DB_PATH = init_db()


def latest_exports(limit: int = 5) -> List[Path]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    items = sorted(EXPORTS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return items[:limit]


def top_tickers(limit: int = 5) -> List[Tuple[str, float, int]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT ticker, AVG(COALESCE(rr,0)) AS avg_rr, COUNT(*) AS trades
            FROM trades
            GROUP BY ticker
            HAVING trades > 0
            ORDER BY avg_rr DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [(row[0], row[1] or 0.0, row[2]) for row in rows]


def render_markdown() -> str:
    today = dt.date.today().strftime("%Y-%m-%d")
    lines = [f"# Daily Ops — {today}", ""]

    winners = top_tickers()
    lines.append("## Top tickers by R:R")
    if winners:
        for ticker, avg_rr, count in winners:
            lines.append(f"- **{ticker}** · R:R {avg_rr:.2f} over {count} trades")
    else:
        lines.append("- _No trades logged yet._")
    lines.append("")

    exports = latest_exports()
    lines.append("## Latest exports")
    if exports:
        for path in exports:
            lines.append(f"- {path.name}")
    else:
        lines.append("- _No exports found in obsidian/90_exports yet._")
    lines.append("")

    lines.append("---")
    lines.append("Synced automatically by daily_ops.py")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    note_path = OUT_DIR / f"{dt.date.today().strftime('%Y-%m-%d')}-daily-ops.md"
    note_path.write_text(render_markdown(), encoding="utf-8")
    print(f"[daily_ops] wrote {note_path}")


if __name__ == "__main__":
    main()
