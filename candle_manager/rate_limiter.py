"""
Per-exchange rate limiters with thread-safe sliding-window accounting.

Key design decisions:
- Sliding-window (not fixed-window) for smoother budget utilisation.
- Optional *weight* tracking: some exchanges (Binance) charge variable
  weight per request, so the limiter tracks a weight budget in addition
  to a raw request count.
- **Release lock BEFORE sleeping** — a critical fix from the audit that
  prevents the lock from being held while the thread sleeps, which would
  block other threads unnecessarily.
- Configurable *margin fraction* (default 0.9) so we stay under the
  hard limit with a small safety buffer.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for a single rate limiter.

    Attributes:
        window_seconds: Size of the sliding window in seconds.
        max_requests: Maximum number of requests allowed inside the window.
        track_weight: Whether to track cumulative request weight.
        max_weight: Maximum weight budget per window (only used if
            ``track_weight`` is ``True``).
        margin_fraction: Fraction of the budget to actually use (0–1).
            A value of 0.9 means we treat 90 % of the limit as the ceiling,
            leaving a 10 % safety margin.
    """

    window_seconds: float
    max_requests: int
    track_weight: bool = False
    max_weight: int = 0
    margin_fraction: float = 0.9

    @property
    def effective_max_requests(self) -> int:
        """Request cap after applying the margin fraction."""
        return int(self.max_requests * self.margin_fraction)

    @property
    def effective_max_weight(self) -> int:
        """Weight cap after applying the margin fraction."""
        return int(self.max_weight * self.margin_fraction)


# ---------------------------------------------------------------------------
# Pre-built configs for each exchange
# ---------------------------------------------------------------------------

BINANCE_SPOT_CONFIG = RateLimitConfig(
    window_seconds=60,
    max_requests=1200,
    track_weight=True,
    max_weight=6000,
    margin_fraction=0.9,
)

BINANCE_FUTURES_CONFIG = RateLimitConfig(
    window_seconds=60,
    max_requests=2400,
    track_weight=True,
    max_weight=2400,
    margin_fraction=0.9,
)

BYBIT_CONFIG = RateLimitConfig(
    window_seconds=5,
    max_requests=600,
    track_weight=False,
    max_weight=0,
    margin_fraction=0.9,
)

DERIBIT_CONFIG = RateLimitConfig(
    window_seconds=1,
    max_requests=20,
    track_weight=False,
    max_weight=0,
    margin_fraction=0.9,
)


class RateLimiter:
    """Thread-safe sliding-window rate limiter with optional weight tracking.

    Usage::

        limiter = RateLimiter("binance_spot", BINANCE_SPOT_CONFIG)
        limiter.wait_if_needed(weight=5)
        # ... make the API call ...

    The limiter keeps a list of ``(timestamp, weight)`` tuples.  On each
    ``wait_if_needed`` call it:

    1. Evicts entries older than ``window_seconds``.
    2. Checks whether adding *weight* would breach the budget.
    3. If the budget is exceeded, calculates how long to sleep, **releases
       the lock**, sleeps, then re-acquires and re-checks.
    """

    def __init__(self, name: str, config: RateLimitConfig) -> None:
        """Initialise the rate limiter.

        Args:
            name: Human-readable identifier (e.g. ``"binance_spot"``).
            config: The rate-limit configuration to use.
        """
        self.name = name
        self.config = config
        self._lock = threading.Lock()
        # List of (timestamp_seconds, weight) tuples.
        self._window: List[tuple[float, int]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_stale(self, now: float) -> None:
        """Remove entries that have fallen outside the sliding window.

        **Must** be called while holding ``self._lock``.

        Args:
            now: Current time in seconds since the epoch.
        """
        cutoff = now - self.config.window_seconds
        self._window = [
            (ts, w) for ts, w in self._window if ts > cutoff
        ]

    def _current_counts(self, now: float) -> tuple[int, int]:
        """Return (request_count, total_weight) after eviction.

        **Must** be called while holding ``self._lock``.

        Args:
            now: Current time since epoch.

        Returns:
            A tuple ``(request_count, total_weight)``.
        """
        self._evict_stale(now)
        request_count = len(self._window)
        total_weight = sum(w for _, w in self._window)
        return request_count, total_weight

    def _would_exceed(self, weight: int, now: float) -> bool:
        """Check if adding *weight* would exceed the budget.

        **Must** be called while holding ``self._lock``.

        Args:
            weight: The weight of the prospective request.
            now: Current time since epoch.

        Returns:
            ``True`` if the budget would be exceeded.
        """
        request_count, total_weight = self._current_counts(now)

        if request_count + 1 > self.config.effective_max_requests:
            return True

        if self.config.track_weight:
            if total_weight + weight > self.config.effective_max_weight:
                return True

        return False

    def _record(self, weight: int, now: float) -> None:
        """Record a request in the sliding window.

        **Must** be called while holding ``self._lock``.

        Args:
            weight: The weight of the request.
            now: Current time since epoch.
        """
        self._window.append((now, weight))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait_if_needed(self, weight: int = 1) -> None:
        """Block the calling thread until *weight* budget is available.

        This is the primary entry point for callers.  It will:

        1. Check the current budget under the lock.
        2. If the budget is exceeded, calculate the sleep duration,
           **release the lock**, sleep, then re-acquire and re-check.
        3. Repeat until the budget is available.
        4. Record the request and return.

        Args:
            weight: The weight to reserve (default 1).
        """
        while True:
            with self._lock:
                now = time.monotonic()
                if not self._would_exceed(weight, now):
                    self._record(weight, now)
                    return

                # Determine how long the oldest entry in the window needs
                # to age out.
                self._evict_stale(now)
                if self._window:
                    oldest_ts = self._window[0][0]
                    sleep_until = oldest_ts + self.config.window_seconds
                    sleep_duration = max(0.0, sleep_until - now)
                else:
                    sleep_duration = 0.1  # Small fallback

            # *** RELEASE LOCK BEFORE SLEEPING ***
            logger.debug(
                f"Rate limiter '{self.name}': budget exceeded "
                f"(weight={weight}). Sleeping {sleep_duration:.2f}s …"
            )
            time.sleep(sleep_duration + 0.05)  # tiny extra margin

    def available_budget(self) -> Dict[str, int | float]:
        """Return the current remaining budget (for monitoring / debugging).

        Returns:
            A dict with keys ``"requests_remaining"`` and
            ``"weight_remaining"`` (or ``None`` if weight tracking is off).
        """
        with self._lock:
            now = time.monotonic()
            request_count, total_weight = self._current_counts(now)
            return {
                "requests_remaining": max(
                    0, self.config.effective_max_requests - request_count
                ),
                "weight_remaining": (
                    max(0, self.config.effective_max_weight - total_weight)
                    if self.config.track_weight
                    else None
                ),
            }


# ---------------------------------------------------------------------------
# Registry — create rate limiters by exchange name
# ---------------------------------------------------------------------------

_EXCHANGE_CONFIGS: Dict[str, RateLimitConfig] = {
    "binance_spot": BINANCE_SPOT_CONFIG,
    "binance_futures": BINANCE_FUTURES_CONFIG,
    "bybit": BYBIT_CONFIG,
    "deribit": DERIBIT_CONFIG,
}


def create_rate_limiter(exchange: str) -> RateLimiter:
    """Factory: create a ``RateLimiter`` for the given exchange.

    Args:
        exchange: One of ``"binance_spot"``, ``"binance_futures"``,
            ``"bybit"``, ``"deribit"``.

    Returns:
        A configured ``RateLimiter`` instance.

    Raises:
        ValueError: If *exchange* is not in the registry.
    """
    config = _EXCHANGE_CONFIGS.get(exchange)
    if config is None:
        raise ValueError(
            f"No rate-limit config for exchange '{exchange}'. "
            f"Available: {list(_EXCHANGE_CONFIGS.keys())}"
        )
    return RateLimiter(exchange, config)
