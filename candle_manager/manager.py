"""
MarketDataManager — the single entry point for all market data operations.

This module ties together the source layer, cache layer, rate limiters,
and symbol mapper into a cohesive API.  Users instantiate
``MarketDataManager`` and call ``get()`` to retrieve data; the manager
handles cache resolution, gap detection, incremental fetching, merging,
and deduplication transparently.
"""

from __future__ import annotations

from typing import List, Optional, Union

import pandas as pd
from loguru import logger

from .cache import CacheStore
from .exceptions import InvalidMetricError, InvalidSymbolError
from .models import Metric, Request
from .rate_limiter import RateLimiter, create_rate_limiter
from .sources import (
    BinanceFundingRateSource,
    BinanceSpotSource,
    BinanceTakerVolumeSource,
    BybitLongShortRatioSource,
    BybitOpenInterestSource,
    DeribitLiquidationsSource,
)
from .sources.base import BaseSource
from .symbol_mapper import SymbolMapper


class MarketDataManager:
    """Single entry point for fetching and caching market data.

    Usage::

        mdm = MarketDataManager()
        df = mdm.get("ohlcv", "BTC/USDT", "1h",
                      since="2024-01-01", until="2024-01-31")

    The manager:
    - Routes each ``Metric`` to the appropriate ``BaseSource``.
    - Resolves cache gaps incrementally — only fetching data that is
      missing from the cache.
    - Merges, deduplicates, and sorts the result before returning.
    - Supports special handling for liquidations (raw cache + resampling).

    Args:
        cache_dir: Root directory for the pickle cache.
    """

    def __init__(self, cache_dir: str = "./cache/market_data") -> None:
        self._cache = CacheStore(cache_dir)
        self._symbol_mapper = SymbolMapper()

        # Create per-exchange rate limiters.
        self._rate_limiters: dict[str, RateLimiter] = {
            "binance_spot": create_rate_limiter("binance_spot"),
            "binance_futures": create_rate_limiter("binance_futures"),
            "bybit": create_rate_limiter("bybit"),
            "deribit": create_rate_limiter("deribit"),
        }

        # Instantiate source objects.
        self._sources: dict[Metric, BaseSource] = {
            Metric.OHLCV: BinanceSpotSource(
                self._rate_limiters["binance_spot"],
                self._symbol_mapper,
            ),
            Metric.FUNDING_RATE: BinanceFundingRateSource(
                self._rate_limiters["binance_futures"],
                self._symbol_mapper,
            ),
            Metric.TAKER_VOLUME: BinanceTakerVolumeSource(
                self._rate_limiters["binance_futures"],
                self._symbol_mapper,
            ),
            Metric.OPEN_INTEREST: BybitOpenInterestSource(
                self._rate_limiters["bybit"],
                self._symbol_mapper,
            ),
            Metric.LONG_SHORT_RATIO: BybitLongShortRatioSource(
                self._rate_limiters["bybit"],
                self._symbol_mapper,
            ),
            Metric.LIQUIDATIONS: DeribitLiquidationsSource(
                self._rate_limiters["deribit"],
                self._symbol_mapper,
            ),
        }

        logger.info("MarketDataManager initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        metric: Union[str, Metric],
        symbol: str,
        timeframe: str,
        *,
        since: Optional[Union[str, pd.Timestamp]] = None,
        until: Optional[Union[str, pd.Timestamp]] = None,
        limit: Optional[int] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Fetch market data, using the cache where possible.

        The method:
        1. Normalises *metric* to a ``Metric`` enum member.
        2. Converts *since* / *until* to UTC ``pd.Timestamp``.
        3. Validates *timeframe* against the source's supported list.
        4. Resolves cache gaps — fetches only what is missing.
        5. Merges, deduplicates, sorts, and saves.
        6. Filters to the requested date range and applies *limit*.

        Args:
            metric: Metric name (string or ``Metric`` enum).
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Interval string, e.g. ``"1h"``.
            since: Start of the time window (UTC).
            until: End of the time window (UTC).
            limit: Maximum number of rows to return (applied last,
                keeping the *newest* rows).
            force_refresh: If ``True``, skip the cache and re-fetch
                everything.

        Returns:
            A ``pd.DataFrame`` with UTC ``DatetimeIndex`` named
            ``"timestamp"``, sorted ascending, no duplicates.

        Raises:
            InvalidMetricError: If *metric* is not recognised.
            InvalidSymbolError: If *symbol* is not supported.
        """
        # 1. Normalise metric.
        if isinstance(metric, str):
            try:
                metric = Metric.from_string(metric)
            except ValueError:
                raise InvalidMetricError(metric)

        source = self._sources.get(metric)
        if source is None:
            raise InvalidMetricError(metric.value)

        # Validate symbol support.
        if not self._symbol_mapper.is_supported(symbol, source.exchange):
            raise InvalidSymbolError(symbol, source.exchange)

        # 2. Convert since/until.
        since_ts = self._to_utc_timestamp(since) if since is not None else None
        until_ts = self._to_utc_timestamp(until) if until is not None else None

        # 3. Validate timeframe.
        source.validate_timeframe(timeframe)

        # 4. Resolve cache gaps and fetch.
        if metric == Metric.LIQUIDATIONS:
            df = self._resolve_liquidations(
                source, symbol, timeframe, since_ts, until_ts, force_refresh,
            )
        else:
            df = self._resolve_cache_gaps(
                source, metric, symbol, timeframe, since_ts, until_ts,
                force_refresh,
            )

        # 5. Filter to requested date range.
        if since_ts is not None:
            df = df[df.index >= since_ts]
        if until_ts is not None:
            df = df[df.index < until_ts]

        # 6. Apply limit (keep the newest rows).
        if limit is not None and limit > 0 and len(df) > limit:
            df = df.iloc[-limit:]

        return df

    def refresh_cache(
        self,
        metric: Union[str, Metric],
        symbol: str,
        timeframe: str,
    ) -> pd.DataFrame:
        """Force-refresh the cache for the given metric/symbol/timeframe.

        Equivalent to ``get()`` with ``until=now`` and
        ``force_refresh=True``.

        Args:
            metric: Metric name.
            symbol: Canonical symbol.
            timeframe: Interval string.

        Returns:
            The refreshed DataFrame.
        """
        return self.get(
            metric, symbol, timeframe,
            until=pd.Timestamp.now(tz="UTC"),
            force_refresh=True,
        )

    def clear_cache(
        self,
        metric: Optional[Union[str, Metric]] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> int:
        """Delete cache files matching the given criteria.

        Any argument that is ``None`` acts as a wildcard.

        Args:
            metric: Metric to match (or ``None`` for all).
            symbol: Symbol to match (or ``None`` for all).
            timeframe: Timeframe to match (or ``None`` for all).

        Returns:
            Number of cache files deleted.
        """
        metric_str = None
        if metric is not None:
            if isinstance(metric, str):
                metric_str = Metric.from_string(metric).value
            else:
                metric_str = metric.value
        return self._cache.delete(metric=metric_str, symbol=symbol,
                                  timeframe=timeframe)

    def cache_info(self) -> pd.DataFrame:
        """Return a summary of all cached data.

        Returns:
            A ``pd.DataFrame`` with columns: metric, symbol, timeframe,
            rows, earliest, latest, size_kb.
        """
        return self._cache.info()

    def available_metrics(self) -> List[Metric]:
        """Return the list of supported metrics.

        Returns:
            List of ``Metric`` enum members.
        """
        return list(self._sources.keys())

    def available_symbols(self, metric: Union[str, Metric] = Metric.OHLCV) -> List[str]:
        """Return the list of symbols supported for the given metric.

        Args:
            metric: The metric to query (default: OHLCV).

        Returns:
            Sorted list of canonical symbol strings.
        """
        if isinstance(metric, str):
            metric = Metric.from_string(metric)
        source = self._sources.get(metric)
        if source is None:
            return []
        return self._symbol_mapper.supported_symbols(source.exchange)

    # ------------------------------------------------------------------
    # Cache-gap resolution (standard metrics)
    # ------------------------------------------------------------------

    def _resolve_cache_gaps(
        self,
        source: BaseSource,
        metric: Metric,
        symbol: str,
        timeframe: str,
        since: Optional[pd.Timestamp],
        until: Optional[pd.Timestamp],
        force_refresh: bool,
    ) -> pd.DataFrame:
        """Detect gaps in the cache and fetch only what is missing.

        Strategy:
        - If ``force_refresh`` or no cache: fetch everything.
        - If cache exists:
          - Detect if *older* data is needed (since < cache start).
          - Detect if *newer* data is needed (until > cache end).
          - For each gap, call ``source.fetch()``.
          - Merge all pieces, deduplicate, sort, save.

        Args:
            source: The data source instance.
            metric: The metric enum member.
            symbol: Canonical symbol.
            timeframe: Interval string.
            since: Requested start (UTC).
            until: Requested end (UTC).
            force_refresh: Skip cache if True.

        Returns:
            Complete DataFrame covering the requested range.
        """
        metric_str = metric.value

        if force_refresh:
            logger.info(
                f"Force refresh: fetching {metric_str} {symbol} {timeframe}"
            )
            df = source.fetch(symbol, timeframe, since=since, until=until)
            if not df.empty:
                self._cache.save(df, metric_str, symbol, timeframe)
            return df

        # Load from cache.
        cached = self._cache.load(metric_str, symbol, timeframe)

        if cached is None or cached.empty:
            logger.info(
                f"Cache miss: fetching {metric_str} {symbol} {timeframe}"
            )
            df = source.fetch(symbol, timeframe, since=since, until=until)
            if not df.empty:
                self._cache.save(df, metric_str, symbol, timeframe)
            return df

        # Cache exists — detect gaps.
        logger.debug(
            f"Cache hit: {metric_str} {symbol} {timeframe} "
            f"({len(cached)} rows, {cached.index.min()} → {cached.index.max()})"
        )

        pieces: list[pd.DataFrame] = [cached]

        # Gap: older data needed?
        if since is not None and since < cached.index.min():
            gap_end = cached.index.min()
            logger.info(
                f"Gap detected (older data): fetching {since} → {gap_end}"
            )
            older = source.fetch(symbol, timeframe, since=since, until=gap_end)
            if not older.empty:
                pieces.append(older)

        # Gap: newer data needed?
        cache_end = cached.index.max()
        effective_until = until if until is not None else pd.Timestamp.now(tz="UTC")
        if effective_until > cache_end:
            # Add one timeframe step to avoid re-fetching the last cached bar.
            gap_start = cache_end + self._timeframe_to_timedelta(timeframe)
            if gap_start < effective_until:
                logger.info(
                    f"Gap detected (newer data): fetching {gap_start} → "
                    f"{effective_until}"
                )
                newer = source.fetch(
                    symbol, timeframe, since=gap_start, until=effective_until,
                )
                if not newer.empty:
                    pieces.append(newer)

        # Merge, deduplicate, sort.
        if len(pieces) == 1:
            return cached

        merged = pd.concat(pieces)
        merged = merged[~merged.index.duplicated(keep="first")]
        merged = merged.sort_index()

        # Save the merged result.
        self._cache.save(merged, metric_str, symbol, timeframe)
        logger.info(
            f"Cache updated: {metric_str} {symbol} {timeframe} "
            f"({len(merged)} rows)"
        )

        return merged

    # ------------------------------------------------------------------
    # Liquidations — special handling
    # ------------------------------------------------------------------

    def _resolve_liquidations(
        self,
        source: BaseSource,
        symbol: str,
        timeframe: str,
        since: Optional[pd.Timestamp],
        until: Optional[pd.Timestamp],
        force_refresh: bool,
    ) -> pd.DataFrame:
        """Resolve liquidations using raw cache + resampling.

        Liquidations are cached at the *raw event* level
        (``liquidations_raw/{symbol}.pkl``) because the API returns
        individual events with no timeframe.  Resampling to the
        requested timeframe happens after loading the raw cache.

        Args:
            source: The DeribitLiquidationsSource.
            symbol: Canonical symbol (BTC/USDT or ETH/USDT).
            timeframe: Resampling interval.
            since: Start timestamp.
            until: End timestamp.
            force_refresh: Skip cache if True.

        Returns:
            Resampled liquidations DataFrame.
        """
        # Import DeribitLiquidationsSource for resampling.
        from .sources.deribit import DeribitLiquidationsSource

        deribit = source  # type: DeribitLiquidationsSource

        if force_refresh:
            raw = deribit.fetch(symbol, timeframe, since=since, until=until)
            return raw

        # Load raw cache.
        raw_cached = self._cache.load_raw(symbol)

        if raw_cached is None or raw_cached.empty:
            # Fetch raw events and cache them.
            raw_events = deribit._fetch_raw_events(
                symbol,
                DeribitLiquidationsSource._SUPPORTED_CURRENCIES.get(symbol, symbol.split("/")[0]),
                since,
                until,
            )
            if not raw_events.empty:
                self._cache.save_raw(raw_events, symbol)
            # Resample.
            if raw_events.empty:
                return deribit._empty_liquidations()
            resampled = deribit._resample(raw_events, timeframe)
            resampled = deribit._normalise_df(resampled)
            return resampled

        # We have raw cache — check if we need to fetch newer events.
        cache_end = raw_cached.index.max()
        effective_until = until if until is not None else pd.Timestamp.now(tz="UTC")

        if effective_until > cache_end:
            gap_start = cache_end
            newer_events = deribit._fetch_raw_events(
                symbol,
                DeribitLiquidationsSource._SUPPORTED_CURRENCIES.get(symbol, symbol.split("/")[0]),
                gap_start,
                effective_until,
            )
            if not newer_events.empty:
                merged_raw = pd.concat([raw_cached, newer_events])
                merged_raw = merged_raw[~merged_raw.index.duplicated(keep="first")]
                merged_raw = merged_raw.sort_index()
                self._cache.save_raw(merged_raw, symbol)
                raw_cached = merged_raw

        # Also check if we need older data.
        if since is not None and since < raw_cached.index.min():
            older_events = deribit._fetch_raw_events(
                symbol,
                DeribitLiquidationsSource._SUPPORTED_CURRENCIES.get(symbol, symbol.split("/")[0]),
                since,
                raw_cached.index.min(),
            )
            if not older_events.empty:
                merged_raw = pd.concat([older_events, raw_cached])
                merged_raw = merged_raw[~merged_raw.index.duplicated(keep="first")]
                merged_raw = merged_raw.sort_index()
                self._cache.save_raw(merged_raw, symbol)
                raw_cached = merged_raw

        # Resample the raw events.
        resampled = deribit._resample(raw_cached, timeframe)
        resampled = deribit._normalise_df(resampled)

        # Also save the resampled result in the regular cache for info().
        self._cache.save(resampled, "liquidations", symbol, timeframe)

        return resampled

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_utc_timestamp(value: Union[str, pd.Timestamp]) -> pd.Timestamp:
        """Convert a string or Timestamp to a UTC-aware pd.Timestamp.

        Args:
            value: A date string or ``pd.Timestamp``.

        Returns:
            A UTC-localised ``pd.Timestamp``.
        """
        ts = pd.Timestamp(value)
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts

    @staticmethod
    def _timeframe_to_timedelta(timeframe: str) -> pd.Timedelta:
        """Convert a timeframe string like ``"1h"`` to a ``pd.Timedelta``.

        Args:
            timeframe: Interval string.

        Returns:
            The corresponding ``pd.Timedelta``.
        """
        # Handle common suffixes: m=minutes, h=hours, d=days, w=weeks, M=months.
        unit = timeframe[-1]
        value = int(timeframe[:-1])

        if unit == "m":
            return pd.Timedelta(minutes=value)
        elif unit == "h":
            return pd.Timedelta(hours=value)
        elif unit == "d":
            return pd.Timedelta(days=value)
        elif unit == "w":
            return pd.Timedelta(weeks=value)
        elif unit == "M":
            # Approximate month as 30 days.
            return pd.Timedelta(days=30 * value)
        else:
            return pd.Timedelta(hours=1)  # Fallback
