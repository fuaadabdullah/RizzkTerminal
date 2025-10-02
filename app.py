"""Application bootstrap for the Rizzk Terminal Dash app."""

from __future__ import annotations

import os
from pathlib import Path

from dash import Dash
from diskcache import Cache as DiskCache
from dotenv import load_dotenv
from flask import Flask, Response, jsonify
from flask_caching import Cache

from rizzk.core.data import load_source
from rizzk.core.db import init as init_db
from rizzk.core.logging import setup_logger
from rizzk.web import register
from rizzk.web.layout import make_layout

ENV_TEMPLATE = (
    "ALPACA_KEY=\n"
    "ALPACA_SECRET=\n"
    "RIZZK_VAULT=C:\\Users\\fuaad\\OneDrive\\Documents\\trading_terminal\\vault\n"
    "OPENAI_API_KEY=\n"
)


def _ensure_env() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")


_ensure_env()
load_dotenv()
setup_logger()

try:  # Optional error telemetry
    import sentry_sdk
except ModuleNotFoundError:  # pragma: no cover - sentry is optional in some environments
    sentry_sdk = None  # type: ignore[assignment]

if sentry_sdk is not None:
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.05, profiles_sample_rate=0.0)

init_db()

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

LONG_TASK_CACHE_DIR = Path(".longcache")
LONG_TASK_CACHE_DIR.mkdir(exist_ok=True)

server = Flask(__name__)
server.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
cache = Cache(
    server,
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": str(CACHE_DIR),
        "CACHE_DEFAULT_TIMEOUT": 300,
    },
)

app = Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    title="Rizzk Terminal",
)
app.layout = make_layout()

source = load_source()
diskcache_backend = DiskCache(str(LONG_TASK_CACHE_DIR))
register(app, cache, source, diskcache_backend)


@server.get("/health")
def healthcheck() -> Response:
    """Return a basic health payload."""
    return jsonify({"ok": True})


def run() -> None:
    """Run the Dash development server."""
    app.run_server(host="127.0.0.1", port=8050, debug=True)


if __name__ == "__main__":
    run()
