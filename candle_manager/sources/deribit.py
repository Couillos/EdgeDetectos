"""
Deribit liquidations data source.

This source fetches bankruptcy (liquidation) events from Deribit's
``/api/v2/public/get_last_settlements_by_currency`` endpoint and
resamples them into the requested timeframe.

Key details:
- Only **BTC** and **ETH** perpetuals are supported.
- Raw events are cached separately (``liquidations_raw/{symbol}.pkl``)
  so that subsequent requests for different timeframes don't need to
  re-fetch from the API.
- The API returns **session-level bankruptcy aggregates** (not individual
  per-position liquidations).  Each record contains:
  ``session_bankruptcy``, ``funded``, ``socialized``, etc.
- Because the Deribit bankruptcy endpoint does not distinguish between
  long and short liquidations, the total ``session_bankruptcy`` is
  reported as ``long_size`` and ``short_size`` is set to 0.  The
  ``long_avg_price`` is estimated from
  ``session_profit_loss / session_bankruptcy`` when available.
- Pagination is continuation-based.
- Symbol mapping: ``"BTC/USDT"`` → ``currency="BTC"``,
  ``"ETH/USDT"`` → ``currency="ETH"``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from loguru import logger

from ..exceptions import InvalidSymbolError, SourceUnavailableError
from ..models import Metric
from ..rate_limiter import RateLimiter
from ..symbol_mapper import SymbolMapper
from .base import BaseSource


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.deribit.com/api/v2"
_REQUEST_TIMEOUT = 30


class DeribitLiquidationsSource(BaseSource):
    """Liquidation events from Deribit.

    Endpoint: ``GET /api/v2/public/get_last_settlements_by_currency``

    The Deribit bankruptcy API returns **session-level aggregates**
    rather than per-position events.  Each record contains the total
    bankruptcy size for a settlement session (typically 8h on Deribit).

    Output columns:
    - ``long_size``        — total bankruptcy size (base currency)
    - ``long_size_usd``    — total bankruptcy size (USD estimate)
    - ``long_avg_price``   — estimated average liquidation price
    - ``short_size``       — 0 (not available from Deribit)
    - ``short_size_usd``   — 0 (not available from Deribit)
    - ``short_avg_price``  — 0 (not available from Deribit)
    """

    # Only BTC and ETH are supported on Deribit.
    _SUPPORTED_CURRENCIES: Dict[str, str] = {
        "BTC/USDT": "BTC",
        "ETH/USDT": "ETH",
    }

    _SUPPORTED_TIMEFRAMES: list[str] = ["1h", "4h", "1d"]

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._session = requests.Session()
        logger.info("DeribitLiquidationsSource initialised")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.LIQUIDATIONS

    @property
    def exchange(self) -> str:
        return "deribit"

    @property
    def supported_timeframes(self) -> list[str]:
        return list(self._SUPPORTED_TIMEFRAMES)

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[pd.Timestamp] = None,
        until: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """Fetch and resample liquidation events from Deribit.

        This method:
        1. Fetches raw liquidation events from the Deribit API.
        2. Resamples them into the requested timeframe.
        3. Returns a DataFrame with long/short size, USD, and avg price.

        Args:
            symbol: Canonical symbol — only ``"BTC/USDT"`` or ``"ETH/USDT"``.
            timeframe: Resampling interval (``"1h"``, ``"4h"``, ``"1d"``).
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            Resampled DataFrame with long/short liquidation aggregates.

        Raises:
            InvalidSymbolError: If *symbol* is not BTC/USDT or ETH/USDT.
            SourceUnavailableError: If the API is unreachable.
        """
        self.validate_timeframe(timeframe)

        if symbol not in self._SUPPORTED_CURRENCIES:
            raise InvalidSymbolError(symbol, "deribit")

        currency = self._SUPPORTED_CURRENCIES[symbol]

        # Fetch raw events.
        raw_df = self._fetch_raw_events(symbol, currency, since, until)

        if raw_df.empty:
            return self._empty_liquidations()

        # Resample.
        resampled = self._resample(raw_df, timeframe)

        # Filter to the requested date range.
        if since is not None:
            resampled = resampled[resampled.index >= since]
        if until is not None:
            resampled = resampled[resampled.index < until]

        return self._normalise_df(resampled)

    # ------------------------------------------------------------------
    # Raw event fetching
    # ------------------------------------------------------------------

    def _fetch_raw_events(
        self,
        symbol: str,
        currency: str,
        since: Optional[pd.Timestamp],
        until: Optional[pd.Timestamp],
    ) -> pd.DataFrame:
        """Fetch raw liquidation events from Deribit with pagination.

        The Deribit API returns session-level bankruptcy aggregates.
        Each record has fields like ``session_bankruptcy``, ``funded``,
        ``socialized``, and ``session_profit_loss``.

        Args:
            symbol: Canonical symbol for logging/caching.
            currency: Deribit currency string (``"BTC"`` or ``"ETH"``).
            since: Start timestamp (UTC).
            until: End timestamp (UTC).

        Returns:
            DataFrame of raw events with columns:
            ``size``, ``size_usd``, ``price``.
        """
        all_events: List[Dict[str, Any]] = []
        continuation: Optional[str] = None
        count = 100  # max records per page
        since_ms = (
            int(since.timestamp() * 1000) if since is not None else None
        )
        until_ms = (
            int(until.timestamp() * 1000) if until is not None else None
        )
        # Safety limit: max pages to fetch to avoid infinite loops.
        max_pages = 50
        pages_fetched = 0

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=1)

                params: Dict[str, Any] = {
                    "currency": currency,
                    "type": "bankruptcy",
                    "count": count,
                }
                if continuation is not None:
                    params["continuation"] = continuation
                # search_start_timestamp: the API returns settlements
                # at or before this timestamp (newest first).
                if until_ms is not None:
                    params["search_start_timestamp"] = until_ms

                logger.debug(
                    f"Fetching liquidations {currency} "
                    f"continuation={continuation}"
                )

                resp = self._session.get(
                    f"{_BASE_URL}/public/get_last_settlements_by_currency",
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                payload = resp.json()

                result = payload.get("result", {})
                settlements = result.get("settlements", [])

                if not settlements:
                    break

                pages_fetched += 1

                # The API returns events newest-first.  Track the oldest
                # timestamp in the current page so we know when to stop.
                oldest_ts_in_page: Optional[int] = None
                for evt in settlements:
                    ts_ms = evt.get("timestamp")
                    if ts_ms is None:
                        continue

                    # Track the oldest event in this page.
                    if oldest_ts_in_page is None or ts_ms < oldest_ts_in_page:
                        oldest_ts_in_page = ts_ms

                    # Skip events outside the requested range.
                    if since_ms is not None and ts_ms < since_ms:
                        continue
                    if until_ms is not None and ts_ms >= until_ms:
                        continue

                    # Extract bankruptcy data from the session aggregate.
                    session_bankruptcy = float(
                        evt.get("session_bankruptcy", 0)
                    )
                    if session_bankruptcy == 0:
                        continue

                    session_profit_loss = float(
                        evt.get("session_profit_loss", 0)
                    )

                    # Estimate average liquidation price from
                    # session_profit_loss / session_bankruptcy.
                    # This is a rough approximation.
                    avg_price = (
                        abs(session_profit_loss) / session_bankruptcy
                        if session_bankruptcy != 0
                        else 0.0
                    )
                    size_usd = session_bankruptcy * avg_price

                    all_events.append(
                        {
                            "timestamp": pd.Timestamp(
                                ts_ms, unit="ms", tz="UTC"
                            ),
                            "size": session_bankruptcy,
                            "size_usd": size_usd,
                            "price": avg_price,
                        }
                    )

                # Check if we need to continue paginating.
                continuation = result.get("continuation")
                if not continuation:
                    break

                # If the oldest event in the current page is before our
                # since boundary, we've gone past the requested window
                # and can stop paginating.
                if since_ms is not None and oldest_ts_in_page is not None:
                    if oldest_ts_in_page < since_ms:
                        logger.debug(
                            f"Stopping pagination: oldest event "
                            f"({pd.Timestamp(oldest_ts_in_page, unit='ms', tz='UTC')}) "
                            f"is before since boundary"
                        )
                        break

                # Safety valve: stop after max_pages to avoid infinite loops.
                if pages_fetched >= max_pages:
                    logger.warning(
                        f"Reached max page limit ({max_pages}) for "
                        f"Deribit liquidations {currency}"
                    )
                    break

        except requests.ConnectionError as exc:
            raise SourceUnavailableError("deribit", str(exc))
        except requests.HTTPError as exc:
            logger.error(f"Deribit HTTP error (liquidations): {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error fetching liquidations: {exc}")

        if not all_events:
            return self._empty_raw_events()

        df = pd.DataFrame(all_events)
        df = df.set_index("timestamp")
        df = df.sort_index()

        return df

    # ------------------------------------------------------------------
    # Resampling
    # ------------------------------------------------------------------

    @staticmethod
    def _resample(raw_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample raw liquidation events into the requested timeframe.

        Since Deribit does not provide long/short breakdown, the total
        bankruptcy size is reported as ``long_size`` with ``short_size``
        set to 0.

        Args:
            raw_df: DataFrame with ``size``, ``size_usd``, ``price``
                columns.
            timeframe: Target frequency, e.g. ``"1h"``.

        Returns:
            Resampled DataFrame with columns:
            ``long_size``, ``long_size_usd``, ``long_avg_price``,
            ``short_size``, ``short_size_usd``, ``short_avg_price``.
        """
        if raw_df.empty:
            return DeribitLiquidationsSource._empty_liquidations()

        # Resample and aggregate.
        resampled = raw_df.resample(timeframe).agg(
            long_size=("size", "sum"),
            long_size_usd=("size_usd", "sum"),
            long_avg_price=("price", "mean"),
        )

        # Add zero short columns (Deribit doesn't provide long/short split).
        resampled["short_size"] = 0.0
        resampled["short_size_usd"] = 0.0
        resampled["short_avg_price"] = 0.0

        # Drop rows where all values are zero.
        resampled = resampled[
            (resampled["long_size"] != 0)
            | (resampled["short_size"] != 0)
        ]

        # Reorder columns.
        ordered = [
            "long_size", "long_size_usd", "long_avg_price",
            "short_size", "short_size_usd", "short_avg_price",
        ]
        resampled = resampled[ordered]

        # Fill NaN with 0.
        resampled = resampled.fillna(0)

        return resampled

    # ------------------------------------------------------------------
    # Empty DataFrames
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_liquidations() -> pd.DataFrame:
        """Return an empty liquidations DataFrame with a UTC DatetimeIndex."""
        df = pd.DataFrame(
            columns=[
                "long_size", "long_size_usd", "long_avg_price",
                "short_size", "short_size_usd", "short_avg_price",
            ],
        )
        df.index = pd.DatetimeIndex([], tz="UTC", name="timestamp")
        return df

    @staticmethod
    def _empty_raw_events() -> pd.DataFrame:
        """Return an empty raw-events DataFrame with a UTC DatetimeIndex."""
        df = pd.DataFrame(columns=["size", "size_usd", "price"])
        df.index = pd.DatetimeIndex([], tz="UTC", name="timestamp")
        return df
