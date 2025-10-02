"""Scheduled data refresh utilities for the Rizzk workspace."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

EXPORTS = Path(os.getenv("RIZZK_EXPORTS", "obsidian/90_exports"))


def fetch_watchlist() -> pd.DataFrame:
    """Return a placeholder watchlist.

    Replace with real data retrieval (broker APIs, etc.) when available.
    """

    return pd.DataFrame(
        [
            {"ticker": "AAPL", "price": 190.12},
            {"ticker": "MSFT", "price": 422.01},
        ]
    )


def main() -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    df = fetch_watchlist()

    csv_path = EXPORTS / f"watchlist_{timestamp}.csv"
    meta_path = EXPORTS / f"watchlist_{timestamp}.json"

    df.to_csv(csv_path, index=False)
    meta_path.write_text(
        json.dumps({"rows": int(len(df)), "generated_at": timestamp}),
        encoding="utf-8",
    )

    print(f"[refresh] wrote {csv_path}")


if __name__ == "__main__":
    main()
