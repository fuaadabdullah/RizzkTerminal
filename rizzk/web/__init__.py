"""Dash web module wiring."""

from __future__ import annotations

from dash import Dash, Input, Output, State, html
from diskcache import Cache as DiskCache
from flask_caching import Cache

from rizzk.core.flags import (
    AI_ENABLED,
    BACKTEST_ENABLED,
    NEWS_ENABLED,
    SCREENER_ENABLED,
)
from rizzk.web.pages import about, ai, backtest, journal, news, prices, screener

DEFAULT_SYMBOL = "AAPL"
SYMBOLS: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "TSLA",
    "AMZN",
    "NVDA",
    "META",
)


def _disabled_panel(message: str) -> html.Div:
    return html.Div([html.H4("Feature disabled"), html.P(message)])


def register(app: Dash, cache: Cache, source, task_cache: DiskCache) -> None:
    """Register callbacks and page renderers with the Dash app."""

    price_renderer, load_prices = prices.register(cache, source)
    screener_renderer = screener.register(cache, load_prices, SYMBOLS)
    journal_renderer = journal.register(app)
    news_renderer = news.register(cache)
    ai_renderer = ai.register()
    about_renderer = about.register()
    backtest_renderer = backtest.register(app, task_cache, load_prices)

    @app.callback(  # type: ignore[misc]
        Output("symbol", "options"),
        Output("symbol", "value"),
        Input("symbol", "id"),
        State("prefs", "data"),
    )
    def _init_symbol(_: str, data: dict | None):  # pragma: no cover - exercised via Dash
        options = [{"label": sym, "value": sym} for sym in SYMBOLS]
        stored = (data or {}).get("symbol") if data else None
        value = stored if stored in SYMBOLS else DEFAULT_SYMBOL
        return options, value

    @app.callback(  # type: ignore[misc]
        Output("prefs", "data"),
        Input("symbol", "value"),
        State("prefs", "data"),
        prevent_initial_call=True,
    )
    def _update_prefs(symbol: str, data: dict | None):  # pragma: no cover - exercised via Dash
        store = data or {}
        store["symbol"] = symbol
        return store

    @app.callback(  # type: ignore[misc]
        Output("page", "children"),
        Input("tabs", "value"),
        State("symbol", "value"),
    )
    def _render_page(tab: str, symbol: str | None):  # pragma: no cover - exercised via Dash
        selected = symbol or DEFAULT_SYMBOL
        if tab == "prices":
            return price_renderer(selected)
        if tab == "screener":
            if not SCREENER_ENABLED:
                return _disabled_panel("Screener disabled by administrator policy.")
            return screener_renderer(selected)
        if tab == "journal":
            return journal_renderer(selected)
        if tab == "news":
            if not NEWS_ENABLED:
                return _disabled_panel("News feed disabled by administrator policy.")
            return news_renderer(selected)
        if tab == "ai":
            if not AI_ENABLED:
                return _disabled_panel("AI features disabled by administrator policy.")
            return ai_renderer(selected)
        if tab == "backtest":
            if not BACKTEST_ENABLED:
                return _disabled_panel("Backtesting disabled by administrator policy.")
            return backtest_renderer(selected)
        if tab == "about":
            return about_renderer(selected)
        return html.Div("Not Found")
