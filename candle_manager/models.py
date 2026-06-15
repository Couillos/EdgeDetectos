"""
Data models and enumerations for the market_data_manager package.

This module defines:
- ``Metric`` — Enum of all supported market-data metrics.
- ``Request`` — Dataclass encapsulating a single data-fetch request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


class Metric(str, Enum):
    """Enumeration of all supported market-data metrics.

    Each member's value is the canonical string key used in cache paths,
    API routing, and serialisation.
    """

    OHLCV = "ohlcv"
    FUNDING_RATE = "funding_rate"
    OPEN_INTEREST = "open_interest"
    TAKER_VOLUME = "taker_volume"
    LIQUIDATIONS = "liquidations"
    LONG_SHORT_RATIO = "long_short_ratio"

    @classmethod
    def from_string(cls, value: str) -> "Metric":
        """Normalise a string (case-insensitive) to a Metric member.

        Args:
            value: A metric name, e.g. ``"ohlcv"`` or ``"OHLCV"``.

        Returns:
            The corresponding ``Metric`` enum member.

        Raises:
            ValueError: If *value* does not match any metric.
        """
        normalised = value.strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        valid = [m.value for m in cls]
        raise ValueError(
            f"Unknown metric '{value}'. Valid metrics: {valid}"
        )


# ---------------------------------------------------------------------------
# DataFrame schema definitions (documentation only — not enforced at runtime)
# ---------------------------------------------------------------------------
# Each metric's ``fetch()`` method returns a ``pd.DataFrame`` with a
# ``DatetimeIndex`` named ``"timestamp"`` in UTC, sorted ascending,
# no duplicates.  The expected column sets are documented here for reference.
#
# OHLCV:            open, high, low, close, volume
# FUNDING_RATE:     funding_rate, mark_price
# OPEN_INTEREST:    open_interest, open_interest_usd
# TAKER_VOLUME:     taker_buy_base, taker_sell_base,
#                   taker_buy_quote, taker_sell_quote,
#                   taker_buy_ratio, taker_sell_ratio
# LIQUIDATIONS:     long_size, long_size_usd, long_avg_price,
#                   short_size, short_size_usd, short_avg_price
# LONG_SHORT_RATIO: buy_ratio, sell_ratio, ls_ratio
# ---------------------------------------------------------------------------


@dataclass
class Request:
    """Encapsulates a single data-fetch request.

    A ``Request`` is the internal representation of what the user asked
    for — it is created by ``MarketDataManager.get()`` and passed through
    the cache / source layers.

    Attributes:
        key: Unique cache key derived from (metric, symbol, timeframe).
        metric: The metric to fetch.
        symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
        timeframe: Candle / sampling interval, e.g. ``"1h"``.
        since: Start of the requested time window (UTC).
        until: End of the requested time window (UTC).
        limit: Maximum number of rows to return (applied after fetch).
        force_refresh: If ``True``, skip the cache and re-fetch everything.
    """

    key: str
    metric: Metric
    symbol: str
    timeframe: str
    since: Optional[pd.Timestamp] = None
    until: Optional[pd.Timestamp] = None
    limit: Optional[int] = None
    force_refresh: bool = False

    @staticmethod
    def build_key(metric: Metric, symbol: str, timeframe: str) -> str:
        """Build a deterministic cache key from metric / symbol / timeframe.

        Args:
            metric: The metric enum member.
            symbol: Canonical symbol string.
            timeframe: Interval string.

        Returns:
            A string like ``"ohlcv_BTC_USDT_1h"``.
        """
        safe_symbol = symbol.replace("/", "_")
        return f"{metric.value}_{safe_symbol}_{timeframe}"
