"""Screener tab implementation."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import pandas_ta as ta
from dash import dash_table, html
from flask_caching import Cache


def register(cache: Cache, load_prices, symbols: Iterable[str]):
    """Register screener helpers."""

    def _compute_rows() -> pd.DataFrame:
        rows: list[dict[str, float]] = []
        for sym in symbols:
            frame = load_prices(sym).copy()
            if frame.empty:
                continue
            indicators = frame.copy()
            indicators["rsi"] = ta.rsi(indicators["close"], length=14)
            indicators["ema20"] = ta.ema(indicators["close"], length=20)
            indicators["atr"] = ta.atr(
                high=indicators["high"],
                low=indicators["low"],
                close=indicators["close"],
                length=14,
            )
            indicators.dropna(inplace=True)
            if indicators.empty:
                continue
            last = indicators.iloc[-1]
            rows.append(
                {
                    "Symbol": sym,
                    "Close": round(float(last["close"]), 2),
                    "RSI": round(float(last["rsi"]), 2),
                    "EMA20": round(float(last["ema20"]), 2),
                    "ATR": round(float(last["atr"]), 2),
                }
            )
        return pd.DataFrame(rows)

    @cache.memoize(timeout=300)
    def _build_table(key: str) -> pd.DataFrame:
        """Return cached screener data (key keeps symbols in the cache key)."""
        return _compute_rows()

    def render(_: str) -> html.Div:
        table_df = _build_table("|".join(sorted(set(symbols))))
        if table_df.empty:
            return html.Div([html.P("No screener data available.")])
        return html.Div(
            [
                html.P("Sortable market metrics for watchlist symbols."),
                dash_table.DataTable(
                    id="screener-table",
                    columns=[{"name": col, "id": col} for col in table_df.columns],
                    data=table_df.to_dict("records"),
                    sort_action="native",
                    filter_action="native",
                    page_size=10,
                    style_table={"overflowX": "auto"},
                ),
            ]
        )

    return render
