"""Ensure the health endpoint responds successfully."""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="session")
def flask_server():
    app_module = importlib.import_module("app")
    return app_module.server


def test_health_endpoint(flask_server) -> None:
    client = flask_server.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
