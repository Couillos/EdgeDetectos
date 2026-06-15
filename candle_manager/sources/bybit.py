"""
Bybit data sources for **open interest** and **long/short ratio**.

Both sources use the Bybit V5 API at ``https://api.bybit.com`` with the
``requests`` library and cursor-based pagination.

The file contains two separate classes:
- ``BybitOpenInterestSource`` — open interest history.
- ``BybitLongShortRatioSource`` — account long/short ratio.

**METHODOLOGY NOTE (Open Interest):**
Before 2026-06-11, Bybit reported *bilateral* open interest (≈2× unilateral).
Values prior to that date are automatically divided by 2, and the resulting
DataFrame has an ``_oi_adjusted`` attribute set to ``True``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from loguru import logger

from ..exceptions import SourceUnavailableError
from ..models import Metric
from ..rate_limiter import RateLimiter
from ..symbol_mapper import SymbolMapper
from .base import BaseSource


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.bybit.com"
_REQUEST_TIMEOUT = 30  # seconds

# Cut-off date for Bybit bilateral OI methodology.
_OI_CUTOFF = pd.Timestamp("2026-06-11", tz="UTC")

# intervalTime / period mapping for Bybit API.
_INTERVAL_MAP: Dict[str, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


# ===========================================================================
# Open Interest
# ===========================================================================

class BybitOpenInterestSource(BaseSource):
    """Open interest data from Bybit V5.

    Endpoint: ``GET /v5/market/open-interest``

    Cursor-based pagination; max 200 records per request.

    Returns a DataFrame with columns:
    - ``open_interest`` (float64)
    - ``open_interest_usd`` (float64)

    Pre-2026-06-11 values are auto-halved to convert from bilateral to
    unilateral convention.  The DataFrame attribute ``_oi_adjusted`` is
    set to ``True`` when this adjustment has been applied.
    """

    _SUPPORTED_TIMEFRAMES: list[str] = ["5m", "15m", "30m", "1h", "4h", "1d"]

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._session = requests.Session()
        logger.info("BybitOpenInterestSource initialised")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.OPEN_INTEREST

    @property
    def exchange(self) -> str:
        return "bybit"

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
        """Fetch open interest history from Bybit.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: One of the supported interval strings.
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            DataFrame with ``open_interest`` and ``open_interest_usd``.

        Raises:
            SourceUnavailableError: If the API is unreachable.
        """
        self.validate_timeframe(timeframe)

        exchange_symbol = self._symbol_mapper.to_exchange(symbol, self.exchange)
        interval = _INTERVAL_MAP[timeframe]

        since_ms = int(since.timestamp() * 1000) if since is not None else None
        until_ms = int(until.timestamp() * 1000) if until is not None else None

        all_records: List[Dict[str, Any]] = []
        cursor = ""
        page_limit = 200

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=1)

                params: Dict[str, Any] = {
                    "category": "linear",
                    "symbol": exchange_symbol,
                    "intervalTime": interval,
                    "limit": page_limit,
                }
                if since_ms is not None:
                    params["startTime"] = since_ms
                if until_ms is not None:
                    params["endTime"] = until_ms
                if cursor:
                    params["cursor"] = cursor

                logger.debug(
                    f"Fetching open interest {exchange_symbol} {timeframe} "
                    f"cursor={cursor[:20] if cursor else 'none'}"
                )

                resp = self._session.get(
                    f"{_BASE_URL}/v5/market/open-interest",
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                payload = resp.json()

                if payload.get("retCode") != 0:
                    logger.warning(
                        f"Bybit API returned retCode={payload.get('retCode')}: "
                        f"{payload.get('retMsg')}"
                    )
                    break

                result = payload.get("result", {})
                rows = result.get("list", [])

                if not rows:
                    break

                all_records.extend(rows)

                cursor = result.get("nextPageCursor", "")
                if not cursor:
                    break

        except requests.ConnectionError as exc:
            raise SourceUnavailableError("bybit", str(exc))
        except requests.HTTPError as exc:
            logger.error(f"Bybit HTTP error (open interest): {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error fetching open interest: {exc}")

        if not all_records:
            return self._empty_open_interest()

        df = pd.DataFrame(all_records)
        df["timestamp"] = pd.to_datetime(
            df["timestamp"].astype(float), unit="ms", utc=True
        )
        df = df.set_index("timestamp")
        df["openInterest"] = pd.to_numeric(df["openInterest"], errors="coerce")

        # openInterestUsd is no longer returned by the Bybit API.
        # We store open_interest in base-currency units and set
        # open_interest_usd to NaN (caller can compute from price).
        if "openInterestUsd" in df.columns:
            df["open_interest_usd"] = pd.to_numeric(
                df["openInterestUsd"], errors="coerce"
            )
        else:
            df["open_interest_usd"] = float("nan")

        df = df[["openInterest", "open_interest_usd"]].copy()
        df.columns = ["open_interest", "open_interest_usd"]

        # Apply bilateral → unilateral adjustment for pre-cutoff data.
        needs_adjustment = df.index < _OI_CUTOFF
        if needs_adjustment.any():
            df.loc[needs_adjustment, "open_interest"] = (
                df.loc[needs_adjustment, "open_interest"] / 2
            )
            df.loc[needs_adjustment, "open_interest_usd"] = (
                df.loc[needs_adjustment, "open_interest_usd"] / 2
            )
            logger.info(
                f"Applied bilateral→unilateral OI adjustment for "
                f"{needs_adjustment.sum()} pre-cutoff rows"
            )

        df = self._normalise_df(df)
        # Mark the adjustment in a custom attribute.
        df.attrs["_oi_adjusted"] = True

        return df

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_open_interest() -> pd.DataFrame:
        """Return an empty open-interest DataFrame."""
        df = pd.DataFrame(columns=["open_interest", "open_interest_usd"])
        df.index.name = "timestamp"
        df.attrs["_oi_adjusted"] = False
        return df


# ===========================================================================
# Long / Short Ratio
# ===========================================================================

class BybitLongShortRatioSource(BaseSource):
    """Account long/short ratio data from Bybit V5.

    Endpoint: ``GET /v5/market/account-ratio``

    Cursor-based pagination; max 500 records per request.
    Earliest data: July 20, 2020.

    Returns a DataFrame with columns:
    - ``buy_ratio`` (float64)
    - ``sell_ratio`` (float64)
    - ``ls_ratio`` (float64) — ``buy_ratio / sell_ratio``
    """

    _SUPPORTED_TIMEFRAMES: list[str] = ["5m", "15m", "30m", "1h", "4h", "1d"]

    # Earliest available data.
    _EARLIEST = pd.Timestamp("2020-07-20", tz="UTC")

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._session = requests.Session()
        logger.info("BybitLongShortRatioSource initialised")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.LONG_SHORT_RATIO

    @property
    def exchange(self) -> str:
        return "bybit"

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
        """Fetch long/short ratio history from Bybit.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: One of the supported interval strings.
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            DataFrame with ``buy_ratio``, ``sell_ratio``, ``ls_ratio``.

        Raises:
            SourceUnavailableError: If the API is unreachable.
        """
        self.validate_timeframe(timeframe)

        exchange_symbol = self._symbol_mapper.to_exchange(symbol, self.exchange)
        period = _INTERVAL_MAP[timeframe]

        since_ms = int(since.timestamp() * 1000) if since is not None else None
        until_ms = int(until.timestamp() * 1000) if until is not None else None

        all_records: List[Dict[str, Any]] = []
        cursor = ""
        page_limit = 500

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=1)

                params: Dict[str, Any] = {
                    "category": "linear",
                    "symbol": exchange_symbol,
                    "period": period,
                    "limit": page_limit,
                }
                if since_ms is not None:
                    params["startTime"] = since_ms
                if until_ms is not None:
                    params["endTime"] = until_ms
                if cursor:
                    params["cursor"] = cursor

                logger.debug(
                    f"Fetching long/short ratio {exchange_symbol} {timeframe} "
                    f"cursor={cursor[:20] if cursor else 'none'}"
                )

                resp = self._session.get(
                    f"{_BASE_URL}/v5/market/account-ratio",
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                payload = resp.json()

                if payload.get("retCode") != 0:
                    logger.warning(
                        f"Bybit API returned retCode={payload.get('retCode')}: "
                        f"{payload.get('retMsg')}"
                    )
                    break

                result = payload.get("result", {})
                rows = result.get("list", [])

                if not rows:
                    break

                all_records.extend(rows)

                cursor = result.get("nextPageCursor", "")
                if not cursor:
                    break

        except requests.ConnectionError as exc:
            raise SourceUnavailableError("bybit", str(exc))
        except requests.HTTPError as exc:
            logger.error(f"Bybit HTTP error (long/short ratio): {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error fetching long/short ratio: {exc}")

        if not all_records:
            return self._empty_ls_ratio()

        df = pd.DataFrame(all_records)

        # Bybit returns timestamp in ms as a string.
        df["timestamp"] = pd.to_datetime(
            df["timestamp"].astype(float), unit="ms", utc=True
        )
        df = df.set_index("timestamp")

        # Convert numeric columns.
        df["buyRatio"] = pd.to_numeric(df["buyRatio"], errors="coerce")
        df["sellRatio"] = pd.to_numeric(df["sellRatio"], errors="coerce")

        df = df[["buyRatio", "sellRatio"]].copy()
        df.columns = ["buy_ratio", "sell_ratio"]
        df["ls_ratio"] = (
            df["buy_ratio"] / df["sell_ratio"].replace(0, float("nan"))
        )

        return self._normalise_df(df)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_ls_ratio() -> pd.DataFrame:
        """Return an empty long/short ratio DataFrame."""
        df = pd.DataFrame(columns=["buy_ratio", "sell_ratio", "ls_ratio"])
        df.index.name = "timestamp"
        return df
