"""Layout primitives for the Dash application."""

from __future__ import annotations

from dash import dcc, html


def make_layout() -> html.Div:
    """Return the root Dash layout."""
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Rizzk Terminal"),
                    dcc.Dropdown(id="symbol", clearable=False),
                ],
                style={"display": "flex", "gap": "12px", "alignItems": "center"},
            ),
            dcc.Tabs(
                id="tabs",
                value="prices",
                children=[
                    dcc.Tab(label="Prices", value="prices"),
                    dcc.Tab(label="Screener", value="screener"),
                    dcc.Tab(label="Journal", value="journal"),
                    dcc.Tab(label="News", value="news"),
                    dcc.Tab(label="AI", value="ai"),
                    dcc.Tab(label="Backtest", value="backtest"),
                    dcc.Tab(label="About", value="about"),
                ],
            ),
            dcc.Store(id="prefs", storage_type="local"),
            html.Div(id="page"),
        ]
    )
