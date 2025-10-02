"""Basic import smoke tests."""

import rizzk  # noqa: F401
from rizzk import web  # noqa: F401
from rizzk.core import (  # noqa: F401
    backtest,
    data,
    db,
    flags,
    journal,
    news,
    security,
    settings,
    util,
)


def test_imports() -> None:
    assert hasattr(rizzk, "core")
