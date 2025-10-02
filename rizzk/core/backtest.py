"""Simple backtest stubs for experimentation."""

from __future__ import annotations

import pandas as pd


def vwap_cross(df: pd.DataFrame) -> pd.DataFrame:
    """Return a naive VWAP cross strategy equity curve."""
    if df.empty:
        return pd.DataFrame(columns=["vwap", "signal", "equity"])

    prices = df.copy()
    volume = prices.get("volume")
    if volume is None:
        volume = pd.Series([1.0] * len(prices), index=prices.index)

    cumulative_volume = volume.cumsum() + 1e-9
    vwap = (prices["close"] * volume).cumsum() / cumulative_volume
    signal = (prices["close"] > vwap).astype(int)
    cross = signal.diff().fillna(0)
    returns = prices["close"].pct_change().fillna(0)
    strategy_returns = returns * signal.shift().fillna(0)
    equity = (1 + strategy_returns).cumprod()
    return pd.DataFrame({"vwap": vwap, "signal": cross, "equity": equity})
