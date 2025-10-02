"""Lightweight data access layer for the terminal."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd


@dataclass
class DataSource:
    """Interface for retrieving data for the UI."""

    def get_ohlc(self, symbol: str, days: int = 200) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError

    def get_news(self, symbol: str, limit: int = 20) -> list[dict]:  # pragma: no cover
        raise NotImplementedError


class YFinanceSource(DataSource):
    """Temporary in-memory price generator used for demos and tests."""

    def get_ohlc(self, symbol: str, days: int = 200) -> pd.DataFrame:
        periods = max(days, 30)
        idx = pd.date_range(end=pd.Timestamp.today(), periods=periods, freq="D")
        rng = np.random.default_rng(abs(hash(symbol)) % (2**32))
        base = rng.normal(loc=0.2, scale=1.5, size=len(idx)).cumsum() + 100
        high = base + rng.random(len(idx)) * 2
        low = base - rng.random(len(idx)) * 2
        open_ = base + rng.normal(0, 0.6, len(idx))
        close = base + rng.normal(0, 0.6, len(idx))
        return pd.DataFrame(
            {
                "date": idx,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.integers(1_000_000, 5_000_000, len(idx)),
            }
        )

    def get_news(self, symbol: str, limit: int = 20) -> list[dict]:
        return [
            {
                "symbol": symbol,
                "title": f"{symbol} placeholder headline #{i + 1}",
                "link": "https://example.com/news",
            }
            for i in range(limit)
        ]


class AlpacaSource(DataSource):
    """Future hook for Alpaca integration."""

    def __init__(self) -> None:
        self.key = os.getenv("ALPACA_KEY")
        self.secret = os.getenv("ALPACA_SECRET")

    def get_ohlc(self, symbol: str, days: int = 200) -> pd.DataFrame:
        # Placeholder until Alpaca integration is implemented.
        return YFinanceSource().get_ohlc(symbol, days)

    def get_news(self, symbol: str, limit: int = 20) -> list[dict]:
        return YFinanceSource().get_news(symbol, limit)


@lru_cache(maxsize=1)
def load_source() -> DataSource:
    """Return the preferred data source based on credentials."""

    if os.getenv("ALPACA_KEY"):
        return AlpacaSource()
    return YFinanceSource()
