"""Helpers for managing local configuration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values

ENV_PATH = Path(".env")


def load_settings() -> Mapping[str, str]:
    """Load key/value pairs from the local environment file."""
    if not ENV_PATH.exists():
        return {}
    return dotenv_values(ENV_PATH)


def save_settings(kv: Mapping[str, str]) -> None:
    """Persist a dictionary of settings to the .env file."""
    lines = [f"{key}={value}" for key, value in kv.items()]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
