"""Risk management helpers for validating trade inputs."""
from __future__ import annotations

from typing import Tuple


def validate_trade(entry: float, stop: float, qty: float, max_risk_dollars: float) -> Tuple[bool, str, float]:
    """Check that the trade respects the configured dollar risk limit."""

    try:
        entry_val = float(entry)
        stop_val = float(stop)
        qty_val = float(qty)
        limit = float(max_risk_dollars)
    except (TypeError, ValueError):
        return False, "Entry, stop, quantity, and risk limit must be numeric.", 0.0

    per_share = abs(entry_val - stop_val)
    if per_share <= 0:
        return False, "Entry and stop must differ to compute risk.", 0.0

    exposure = per_share * max(qty_val, 0.0)
    if exposure <= 0:
        return False, "Quantity must be positive.", 0.0

    if exposure > limit:
        return False, f"Risk ${exposure:.2f} exceeds limit ${limit:.2f}.", exposure

    return True, "", exposure


__all__ = ["validate_trade"]
