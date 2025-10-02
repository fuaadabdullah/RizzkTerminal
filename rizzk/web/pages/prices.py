"""Prices tab rendering and helpers."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from flask_caching import Cache


def register(cache: Cache, source):
    """Register data loaders for the prices page."""

    @cache.memoize()
    def load_prices(symbol: str) -> pd.DataFrame:
        df = source.get_ohlc(symbol, days=200)
        frame = pd.DataFrame(df).copy()
        if not frame.empty:
            frame.sort_values("date", inplace=True)
        return frame

    def render(symbol: str) -> html.Div:
        frame = load_prices(symbol)
        if frame.empty:
            return html.Div([html.P("No price data available.")])

        figure = go.Figure()
        figure.add_trace(go.Scatter(x=frame["date"], y=frame["close"], mode="lines", name=symbol))
        figure.update_layout(
            template="plotly_dark",
            margin=dict(l=30, r=30, t=30, b=30),
            height=520,
            title=f"Closing Prices for {symbol}",
        )
        return html.Div([dcc.Graph(figure=figure)])

    return render, load_prices
