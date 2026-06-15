"""
Binance Futures data sources for **funding rate** and **taker volume**.

Both sources hit the Binance Futures API at ``https://fapi.binance.com``
using the ``requests`` library (NOT ccxt), and share the
``binance_futures`` rate-limiter config.

The file contains two separate classes:
- ``BinanceFundingRateSource`` — per-settlement funding rate data.
- ``BinanceTakerVolumeSource`` — taker buy/sell volume from klines.
"""

from __future__ import annotations

import time
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

_BASE_URL = "https://fapi.binance.com"
_REQUEST_TIMEOUT = 30  # seconds


# ===========================================================================
# Funding Rate
# ===========================================================================

class BinanceFundingRateSource(BaseSource):
    """Funding rate data from Binance Futures.

    Endpoint: ``GET /fapi/v1/fundingRate``

    The Binance funding-rate API returns one record per settlement event.
    The default settlement interval is 8 h, though some contracts use 4 h
    or 2 h.  Because the API only returns data at settlement boundaries,
    we only accept timeframes >= 2 h.

    Returns a DataFrame with columns:
    - ``funding_rate`` (float64)
    - ``mark_price`` (float64)
    """

    _SUPPORTED_TIMEFRAMES: list[str] = ["2h", "4h", "8h"]

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._session = requests.Session()
        logger.info("BinanceFundingRateSource initialised")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.FUNDING_RATE

    @property
    def exchange(self) -> str:
        return "binance_futures"

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
        """Fetch funding rate history from Binance Futures.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Settlement interval — only ``"2h"``, ``"4h"``,
                or ``"8h"`` are accepted.
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            DataFrame with ``funding_rate`` and ``mark_price`` columns.

        Raises:
            SourceUnavailableError: If the API is unreachable.
        """
        self.validate_timeframe(timeframe)

        exchange_symbol = self._symbol_mapper.to_exchange(symbol, self.exchange)

        since_ms = int(since.timestamp() * 1000) if since is not None else None
        until_ms = int(until.timestamp() * 1000) if until is not None else None

        all_records: List[Dict[str, Any]] = []
        page_limit = 1000
        current_start = since_ms

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=1)

                params: Dict[str, Any] = {
                    "symbol": exchange_symbol,
                    "limit": page_limit,
                }
                if current_start is not None:
                    params["startTime"] = current_start
                if until_ms is not None:
                    params["endTime"] = until_ms

                logger.debug(
                    f"Fetching funding rate {exchange_symbol} "
                    f"startTime={current_start}"
                )

                resp = self._session.get(
                    f"{_BASE_URL}/fapi/v1/fundingRate",
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                all_records.extend(data)

                # If we received fewer than page_limit, we're done.
                if len(data) < page_limit:
                    break

                # Advance startTime past the last record.
                last_ts = data[-1]["fundingTime"]  # fundingTime field
                if until_ms is not None and last_ts >= until_ms:
                    break

                current_start = last_ts + 1

        except requests.ConnectionError as exc:
            raise SourceUnavailableError("binance_futures", str(exc))
        except requests.HTTPError as exc:
            logger.error(
                f"Binance Futures HTTP error (funding rate): {exc} "
                f"— status={resp.status_code}"
            )
        except Exception as exc:
            logger.error(f"Unexpected error fetching funding rate: {exc}")

        if not all_records:
            return self._empty_funding_rate()

        df = pd.DataFrame(all_records)
        df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        df = df[["fundingRate", "markPrice"]].copy()
        df.columns = ["funding_rate", "mark_price"]
        df["funding_rate"] = pd.to_numeric(df["funding_rate"], errors="coerce")
        df["mark_price"] = pd.to_numeric(df["mark_price"], errors="coerce")

        return self._normalise_df(df)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_funding_rate() -> pd.DataFrame:
        """Return an empty funding-rate DataFrame."""
        df = pd.DataFrame(columns=["funding_rate", "mark_price"])
        df.index.name = "timestamp"
        return df


# ===========================================================================
# Taker Volume
# ===========================================================================

class BinanceTakerVolumeSource(BaseSource):
    """Taker buy/sell volume data from Binance Futures klines.

    Endpoint: ``GET /fapi/v1/klines``

    We extract taker volume fields from the kline response:
    - kline[5]  = total volume
    - kline[7]  = quote asset volume
    - kline[9]  = taker buy base asset volume
    - kline[10] = taker buy quote asset volume

    From these we derive:
    - ``taker_buy_base``   = kline[9]
    - ``taker_sell_base``  = kline[5] − kline[9]
    - ``taker_buy_quote``  = kline[10]
    - ``taker_sell_quote`` = kline[7] − kline[10]
    - ``taker_buy_ratio``  = buy_base / (buy_base + sell_base)
    - ``taker_sell_ratio`` = sell_base / (buy_base + sell_base)

    The request weight depends on the ``limit`` parameter:
    - 1  for limit ≤ 99
    - 2  for 100–499
    - 5  for 500–999
    - 10 for ≥ 1000

    We use ``limit=1500`` (weight 10) for maximum efficiency.
    """

    _SUPPORTED_TIMEFRAMES: list[str] = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M",
    ]

    # Weight schedule based on limit value.
    _LIMIT_WEIGHT: Dict[int, int] = {
        99: 1,
        499: 2,
        999: 5,
        1500: 10,
    }

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._session = requests.Session()
        logger.info("BinanceTakerVolumeSource initialised")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.TAKER_VOLUME

    @property
    def exchange(self) -> str:
        return "binance_futures"

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
        """Fetch taker volume from Binance Futures klines.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Interval string.
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            DataFrame with taker volume columns (see class docstring).

        Raises:
            SourceUnavailableError: If the API is unreachable.
        """
        self.validate_timeframe(timeframe)

        exchange_symbol = self._symbol_mapper.to_exchange(symbol, self.exchange)

        since_ms = int(since.timestamp() * 1000) if since is not None else None
        until_ms = int(until.timestamp() * 1000) if until is not None else None

        all_candles: List[list] = []
        page_limit = 1500  # weight = 10
        weight = self._weight_for_limit(page_limit)
        current_start = since_ms

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=weight)

                params: Dict[str, Any] = {
                    "symbol": exchange_symbol,
                    "interval": timeframe,
                    "limit": page_limit,
                }
                if current_start is not None:
                    params["startTime"] = current_start
                if until_ms is not None:
                    params["endTime"] = until_ms

                logger.debug(
                    f"Fetching taker volume {exchange_symbol} {timeframe} "
                    f"startTime={current_start} weight={weight}"
                )

                resp = self._session.get(
                    f"{_BASE_URL}/fapi/v1/klines",
                    params=params,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                all_candles.extend(data)

                # Binance kline response is an array of arrays:
                # [0] open_time, [1] open, [2] high, [3] low, [4] close,
                # [5] volume, [6] close_time, [7] quote_volume,
                # [8] num_trades, [9] taker_buy_base_vol,
                # [10] taker_buy_quote_vol, [11] ignore

                # If fewer than page_limit, we're done.
                if len(data) < page_limit:
                    break

                last_open_time = data[-1][0]
                if until_ms is not None and last_open_time >= until_ms:
                    break

                current_start = last_open_time + 1

        except requests.ConnectionError as exc:
            raise SourceUnavailableError("binance_futures", str(exc))
        except requests.HTTPError as exc:
            logger.error(
                f"Binance Futures HTTP error (taker volume): {exc} "
                f"— status={resp.status_code}"
            )
        except Exception as exc:
            logger.error(f"Unexpected error fetching taker volume: {exc}")

        if not all_candles:
            return self._empty_taker_volume()

        # Parse the kline arrays into a DataFrame.
        records = []
        for k in all_candles:
            open_time = k[0]
            total_volume = float(k[5])
            quote_volume = float(k[7])
            taker_buy_base = float(k[9])
            taker_buy_quote = float(k[10])

            taker_sell_base = total_volume - taker_buy_base
            taker_sell_quote = quote_volume - taker_buy_quote

            total_taker_base = taker_buy_base + taker_sell_base
            taker_buy_ratio = (
                taker_buy_base / total_taker_base
                if total_taker_base != 0
                else 0.0
            )
            taker_sell_ratio = (
                taker_sell_base / total_taker_base
                if total_taker_base != 0
                else 0.0
            )

            records.append(
                {
                    "timestamp": pd.Timestamp(open_time, unit="ms", tz="UTC"),
                    "taker_buy_base": taker_buy_base,
                    "taker_sell_base": taker_sell_base,
                    "taker_buy_quote": taker_buy_quote,
                    "taker_sell_quote": taker_sell_quote,
                    "taker_buy_ratio": taker_buy_ratio,
                    "taker_sell_ratio": taker_sell_ratio,
                }
            )

        df = pd.DataFrame(records)
        df = df.set_index("timestamp")

        return self._normalise_df(df)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _weight_for_limit(cls, limit: int) -> int:
        """Return the API weight for the given kline ``limit`` value.

        Args:
            limit: Number of klines requested.

        Returns:
            The request weight (1, 2, 5, or 10).
        """
        if limit <= 99:
            return 1
        elif limit <= 499:
            return 2
        elif limit <= 999:
            return 5
        else:
            return 10

    @staticmethod
    def _empty_taker_volume() -> pd.DataFrame:
        """Return an empty taker-volume DataFrame."""
        df = pd.DataFrame(
            columns=[
                "taker_buy_base", "taker_sell_base",
                "taker_buy_quote", "taker_sell_quote",
                "taker_buy_ratio", "taker_sell_ratio",
            ],
        )
        df.index.name = "timestamp"
        return df
