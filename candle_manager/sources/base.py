"""
Abstract base class for all data sources.

Every source (Binance Spot, Binance Futures, Bybit, Deribit) inherits
from ``BaseSource`` and implements the ``fetch()`` method.  The base
class provides common infrastructure: rate-limiter integration, symbol
mapping, and timeframe validation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd
from loguru import logger

from ..exceptions import InvalidTimeframeError
from ..models import Metric
from ..rate_limiter import RateLimiter
from ..symbol_mapper import SymbolMapper


class BaseSource(ABC):
    """Abstract base for a single metric data source.

    Subclasses must define:
    - ``metric`` property — the ``Metric`` this source provides.
    - ``exchange`` property — exchange identifier string.
    - ``supported_timeframes`` property — list of valid timeframe strings.
    - ``fetch()`` method — the actual data-retrieval logic.

    Args:
        rate_limiter: A configured ``RateLimiter`` for this source's exchange.
        symbol_mapper: The shared ``SymbolMapper`` instance.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._symbol_mapper = symbol_mapper

    # ------------------------------------------------------------------
    # Properties (must be overridden by subclasses)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def metric(self) -> Metric:
        """The ``Metric`` enum member this source provides."""
        ...

    @property
    @abstractmethod
    def exchange(self) -> str:
        """Exchange identifier string, e.g. ``"binance_spot"``."""
        ...

    @property
    @abstractmethod
    def supported_timeframes(self) -> list[str]:
        """List of timeframe strings this source supports."""
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def rate_limiter(self) -> RateLimiter:
        """The ``RateLimiter`` associated with this source."""
        return self._rate_limiter

    @property
    def symbol_mapper(self) -> SymbolMapper:
        """The ``SymbolMapper`` associated with this source."""
        return self._symbol_mapper

    def validate_timeframe(self, timeframe: str) -> None:
        """Raise ``InvalidTimeframeError`` if *timeframe* is not supported.

        Args:
            timeframe: The timeframe string to validate.

        Raises:
            InvalidTimeframeError: If the timeframe is not in
                ``supported_timeframes``.
        """
        if timeframe not in self.supported_timeframes:
            raise InvalidTimeframeError(
                timeframe,
                exchange=self.exchange,
                supported=self.supported_timeframes,
            )

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[pd.Timestamp] = None,
        until: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """Fetch data from the upstream API.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Interval string, e.g. ``"1h"``.
            since: Start of the time window (UTC), inclusive.
            until: End of the time window (UTC), exclusive.

        Returns:
            A ``pd.DataFrame`` with a UTC ``DatetimeIndex`` named
            ``"timestamp"``, sorted ascending, no duplicates.
        """
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _normalise_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure the DataFrame conforms to the package conventions.

        - DatetimeIndex named ``"timestamp"`` in UTC.
        - Sorted ascending.
        - No duplicate indices.

        Args:
            df: Raw DataFrame (may or may not be compliant).

        Returns:
            A normalised DataFrame.
        """
        if df.empty:
            if df.index.name != "timestamp":
                df.index.name = "timestamp"
            return df

        # Ensure DatetimeIndex.
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.DatetimeIndex(df.index)

        # Ensure UTC timezone.
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        df.index.name = "timestamp"

        # Sort and deduplicate.
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="first")]

        return df
