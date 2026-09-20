"""Small process-local fixed-window limiter for authenticated operator actions."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class FixedWindowRateLimiter:
    """Bound requests per key without adding infrastructure to the local-first API."""

    def __init__(self, limit: int = 10, window_seconds: int = 60, *, clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate-limit values must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> FixedWindowRateLimiter:
        return cls(
            limit=int(os.getenv("MCT_OPERATOR_RATE_LIMIT", "10")),
            window_seconds=int(os.getenv("MCT_OPERATOR_RATE_WINDOW_SECONDS", "60")),
        )

    def check(self, key: str) -> RateLimitDecision:
        now = self._clock()
        with self._lock:
            started, count = self._windows.get(key, (now, 0))
            elapsed = now - started
            if elapsed >= self.window_seconds or elapsed < 0:
                started, count = now, 0
            if count >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - started) + 0.999))
                return RateLimitDecision(False, retry_after)
            self._windows[key] = (started, count + 1)
            return RateLimitDecision(True, 0)

    def clear(self) -> None:
        with self._lock:
            self._windows.clear()
