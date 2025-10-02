"""Ensure the health endpoint responds successfully and enforces rate limiting."""

from __future__ import annotations

import importlib
import sys

import pytest


def _load_app():
    module_name = "app"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("HEALTH_RATE_LIMIT", "5")
    monkeypatch.setenv("HEALTH_RATE_WINDOW", "60")
    module = _load_app()
    yield module
    sys.modules.pop("app", None)


def test_health_endpoint(app_module) -> None:
    client = app_module.server.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_health_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("HEALTH_RATE_LIMIT", "1")
    monkeypatch.setenv("HEALTH_RATE_WINDOW", "60")
    module = _load_app()
    client = module.server.test_client()
    first = client.get("/health")
    assert first.status_code == 200
    second = client.get("/health")
    assert second.status_code == 429
    assert second.get_json() == {"ok": False, "error": "rate_limited"}
    module.health_limiter.reset()
    sys.modules.pop("app", None)
