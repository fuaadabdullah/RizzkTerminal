"""Security-related helpers for the web application."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """A simple in-memory rate limiter using a sliding time window."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Return True if the caller with ``key`` has remaining quota."""
        now = time.monotonic()
        window_start = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < window_start:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        """Clear all rate limiter state (useful for tests)."""
        with self._lock:
            self._hits.clear()
