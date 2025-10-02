"""Backtest page with asynchronous execution."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, no_update
from diskcache import Cache as DiskCache

from rizzk.core.backtest import vwap_cross

LOGGER = logging.getLogger(__name__)


def register(app: Dash, task_cache: DiskCache, load_prices: Callable[[str], pd.DataFrame]):
    """Register backtest callbacks and return a renderer."""

    def _run_job(job_id: str, symbol: str) -> None:
        try:
            prices = load_prices(symbol)
            result = vwap_cross(prices)
            payload = {
                "status": "done",
                "equity": result["equity"].tolist(),
                "index": [str(idx) for idx in result.index],
            }
            task_cache.set(job_id, payload)
        except Exception as exc:  # pragma: no cover - background error path
            LOGGER.exception("Backtest failed")
            task_cache.set(job_id, {"status": "error", "error": str(exc)})

    def render(symbol: str) -> html.Div:
        return html.Div(
            [
                html.H3("Backtest"),
                html.P("VWAP cross demo strategy. Executes asynchronously to keep the UI responsive."),
                html.Button("Run Backtest", id="backtest-run", n_clicks=0),
                html.Div(id="backtest-status", className="backtest-status"),
                dcc.Store(id="backtest-job"),
                dcc.Interval(id="backtest-poll", interval=2000, n_intervals=0, disabled=True),
                dcc.Graph(id="backtest-graph"),
            ]
        )

    @app.callback(  # type: ignore[misc]
        Output("backtest-job", "data"),
        Output("backtest-status", "children"),
        Output("backtest-poll", "disabled"),
        Input("backtest-run", "n_clicks"),
        State("symbol", "value"),
        prevent_initial_call=True,
    )
    def _start_job(n_clicks: int, symbol: str):  # pragma: no cover - exercised via Dash
        if not symbol:
            return no_update, "Select a symbol to backtest.", True
        job_id = str(uuid.uuid4())
        task_cache.set(job_id, {"status": "running"})
        threading.Thread(target=_run_job, args=(job_id, symbol), daemon=True).start()
        return job_id, f"Running backtest for {symbol}...", False

    @app.callback(  # type: ignore[misc]
        Output("backtest-status", "children"),
        Output("backtest-graph", "figure"),
        Output("backtest-poll", "disabled"),
        Input("backtest-poll", "n_intervals"),
        State("backtest-job", "data"),
        prevent_initial_call=True,
    )
    def _poll_status(_: int, job_id: str | None):  # pragma: no cover - exercised via Dash
        figure = go.Figure()
        if not job_id:
            return no_update, figure, True
        info = task_cache.get(job_id)
        if not info:
            return "Unknown job.", figure, True
        status = info.get("status")
        if status == "running":
            return "Backtest running...", figure, False
        if status == "error":
            return f"Backtest failed: {info.get('error')}", figure, True
        if status == "done":
            index = info.get("index", [])
            equity = info.get("equity", [])
            if index and equity:
                figure.add_trace(go.Scatter(x=index, y=equity, mode="lines", name="Equity"))
                figure.update_layout(
                    template="plotly_dark",
                    margin=dict(l=30, r=30, t=30, b=30),
                    height=520,
                    title="VWAP Cross Equity Curve",
                )
            return "Backtest complete.", figure, True
        return "Unknown status.", figure, True

    return render
