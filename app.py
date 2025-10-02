"""Dash application entry point for the Rizzk Terminal."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from dash import (
    Dash,
    Input,
    Output,
    State,
    dcc,
    html,
    dash_table,
)
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_caching import Cache

from rizzk.core.data import load_source
from rizzk.core.journal import add_entry, list_entries
from rizzk.core.news import fetch_news
from rizzk.core.util import humanize_timestamp

ENV_TEMPLATE = (
    "ALPACA_KEY=\n"
    "ALPACA_SECRET=\n"
    "RIZZK_VAULT=C:\\Users\\fuaad\\OneDrive\\Documents\\trading_terminal\\vault\n"
    "OPENAI_API_KEY=\n"
)

ENV_PATH = Path(".env")
if not ENV_PATH.exists():
    ENV_PATH.write_text(ENV_TEMPLATE, encoding="utf-8")

load_dotenv()

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

server = Flask(__name__)
cache = Cache(
    server,
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": str(CACHE_DIR),
        "CACHE_DEFAULT_TIMEOUT": 300,
    },
)


def _create_dash_app(flask_server: Flask) -> Dash:
    return Dash(
        __name__,
        server=flask_server,
        suppress_callback_exceptions=True,
        title="Rizzk Terminal",
    )


@server.get("/health")
def healthcheck() -> Any:
    """Return a basic health payload."""
    return jsonify({"ok": True})


app = _create_dash_app(server)
source = load_source()
DEFAULT_SYMBOL = "AAPL"
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META"]


def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="prefs", storage_type="local"),
            html.Header(
                [
                    html.H1("Rizzk Terminal"),
                    html.P("Dash-powered terminal for market research."),
                ],
                className="header",
            ),
            html.Div(
                [
                    html.Label("Symbol"),
                    dcc.Dropdown(
                        id="symbol",
                        options=[{"label": sym, "value": sym} for sym in SYMBOLS],
                        value=DEFAULT_SYMBOL,
                        clearable=False,
                    ),
                ],
                className="controls",
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
                    dcc.Tab(label="Widgets", value="widgets"),
                    dcc.Tab(label="About", value="about"),
                ],
            ),
            html.Div(id="tab-content", className="tab-content"),
        ]
    )


app.layout = serve_layout


@cache.memoize()
def get_prices(symbol: str) -> pd.DataFrame:
    df = source.get_ohlc(symbol, days=200).copy()
    df.sort_values("date", inplace=True)
    return df


@cache.memoize(timeout=600)
def get_news() -> list[dict[str, str]]:
    try:
        return fetch_news(limit=40)
    except Exception as exc:  # pragma: no cover - network failure path
        return [{"source": "Error", "title": str(exc), "link": ""}]


def make_prices_tab(symbol: str) -> html.Div:
    df = get_prices(symbol)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], mode="lines", name=symbol))
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=30, r=30, t=30, b=30),
        height=520,
        title=f"Closing Prices for {symbol}",
    )
    return html.Div([dcc.Graph(figure=fig)])


def build_screener(symbols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for sym in symbols:
        df = get_prices(sym).copy()
        indicators = df.copy()
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


def make_screener_tab(symbols: list[str]) -> html.Div:
    table_df = build_screener(symbols)
    if table_df.empty:
        table_df = pd.DataFrame(columns=["Symbol", "Close", "RSI", "EMA20", "ATR"])
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


def format_journal_rows(limit: int = 50) -> list[dict[str, str]]:
    entries = list_entries(limit=limit)
    return [
        {
            "id": str(entry["id"]),
            "timestamp": humanize_timestamp(entry["ts"]),
            "body": entry["body"],
        }
        for entry in entries
    ]


def make_journal_tab() -> html.Div:
    return html.Div(
        [
            html.Div(id="journal-message", className="journal-message"),
            dcc.Textarea(id="journal-text", style={"width": "100%", "height": "120px"}),
            html.Button("Save Entry", id="journal-save", n_clicks=0),
            dash_table.DataTable(
                id="journal-table",
                columns=[
                    {"name": "ID", "id": "id"},
                    {"name": "Timestamp", "id": "timestamp"},
                    {"name": "Entry", "id": "body"},
                ],
                data=format_journal_rows(),
                style_table={"overflowY": "auto", "maxHeight": "320px"},
            ),
        ]
    )


def make_news_tab() -> html.Div:
    items = get_news()
    return html.Div(
        [
            html.Ul(
                [
                    html.Li(
                        html.A(
                            f"{item['source']}: {item['title']}",
                            href=item["link"] or "#",
                            target="_blank",
                            rel="noopener noreferrer",
                        )
                    )
                    for item in items
                ],
                className="news-list",
            )
        ]
    )


def make_ai_tab() -> html.Div:
    if not os.getenv("OPENAI_API_KEY"):
        return html.Div(
            [
                html.H3("AI Assistant"),
                html.P(
                    "OpenAI API key not configured. Add OPENAI_API_KEY to .env to enable AI features.",
                ),
            ]
        )
    return html.Div([html.P("AI integrations coming soon.")])


def make_widgets_tab() -> html.Div:
    return html.Div(
        [
            html.H3("Widgets"),
            html.P("Custom dashboards and components will live here."),
        ]
    )


def make_about_tab() -> html.Div:
    return html.Div(
        [
            html.H3("About"),
            html.P("Rizzk Terminal is an experimental research tool for traders."),
            html.P("Built with Dash, Flask, and a lightweight data layer."),
        ]
    )


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    State("symbol", "value"),
)
def render_tab(tab: str, symbol: str) -> html.Div:
    symbol = symbol or DEFAULT_SYMBOL
    if tab == "prices":
        return make_prices_tab(symbol)
    if tab == "screener":
        return make_screener_tab(SYMBOLS)
    if tab == "journal":
        return make_journal_tab()
    if tab == "news":
        return make_news_tab()
    if tab == "ai":
        return make_ai_tab()
    if tab == "widgets":
        return make_widgets_tab()
    if tab == "about":
        return make_about_tab()
    return html.Div("Not Found")


@app.callback(
    Output("journal-message", "children"),
    Output("journal-table", "data"),
    Input("journal-save", "n_clicks"),
    State("journal-text", "value"),
    prevent_initial_call=True,
)
def save_journal_entry(n_clicks: int, text: str) -> tuple[str, list[dict[str, str]]]:
    if not text or not text.strip():
        return "Nothing to save.", format_journal_rows()
    try:
        add_entry(text)
    except ValueError as err:
        return str(err), format_journal_rows()
    return "Saved entry.", format_journal_rows()


@app.callback(
    Output("prefs", "data"),
    Input("symbol", "value"),
    State("prefs", "data"),
    prevent_initial_call=True,
)
def update_prefs(symbol: str, data: dict | None) -> dict:
    store = data or {}
    store["symbol"] = symbol
    return store


@app.callback(Output("symbol", "value"), Input("prefs", "data"))
def load_prefs(data: dict | None) -> str:
    if data and data.get("symbol") in SYMBOLS:
        return data["symbol"]
    return DEFAULT_SYMBOL


if __name__ == "__main__":
    app.run_server(debug=True)
