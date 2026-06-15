"""
Binance Spot OHLCV data source via ccxt.

This source fetches candlestick (OHLCV) data from Binance Spot using
the ``ccxt`` library.  Rate limiting is handled by our own ``RateLimiter``
rather than ccxt's built-in mechanism, so ``enableRateLimit`` is set to
``False``.

Pagination uses the Binance kline API convention of ``startTime`` /
``endTime`` with a page size of 1000 candles.
"""

from __future__ import annotations

from typing import Optional

import ccxt
import pandas as pd
from loguru import logger

from ..exceptions import SourceUnavailableError
from ..models import Metric
from ..rate_limiter import RateLimiter
from ..symbol_mapper import SymbolMapper
from .base import BaseSource


class BinanceSpotSource(BaseSource):
    """OHLCV data from Binance Spot via ccxt.

    Supported timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h,
    12h, 1d, 3d, 1w, 1M.

    Returns a DataFrame with columns: ``open``, ``high``, ``low``,
    ``close``, ``volume``.
    """

    _SUPPORTED_TIMEFRAMES: list[str] = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M",
    ]

    def __init__(
        self,
        rate_limiter: RateLimiter,
        symbol_mapper: SymbolMapper,
    ) -> None:
        super().__init__(rate_limiter, symbol_mapper)
        self._exchange = ccxt.binance({"enableRateLimit": False})
        logger.info("BinanceSpotSource initialised (ccxt)")

    # ------------------------------------------------------------------
    # BaseSource interface
    # ------------------------------------------------------------------

    @property
    def metric(self) -> Metric:
        return Metric.OHLCV

    @property
    def exchange(self) -> str:
        return "binance_spot"

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
        """Fetch OHLCV candles from Binance Spot.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Interval string, e.g. ``"1h"``.
            since: Start timestamp (UTC), inclusive.
            until: End timestamp (UTC), exclusive.

        Returns:
            DataFrame with columns ``open, high, low, close, volume``,
            DatetimeIndex ``"timestamp"`` in UTC, sorted ascending.

        Raises:
            SourceUnavailableError: If the Binance API is unreachable.
        """
        self.validate_timeframe(timeframe)

        # Convert canonical symbol for ccxt (it accepts "BTC/USDT" natively).
        exchange_symbol = self._symbol_mapper.to_exchange(symbol, self.exchange)

        since_ms = int(since.timestamp() * 1000) if since is not None else None
        until_ms = int(until.timestamp() * 1000) if until is not None else None

        all_candles: list[list] = []
        page_limit = 1000
        current_since = since_ms

        try:
            while True:
                self._rate_limiter.wait_if_needed(weight=1)

                logger.debug(
                    f"Fetching OHLCV {exchange_symbol} {timeframe} "
                    f"since={current_since}"
                )

                kwargs: dict = {
                    "symbol": exchange_symbol,
                    "timeframe": timeframe,
                    "limit": page_limit,
                }
                if current_since is not None:
                    kwargs["since"] = current_since
                # ccxt does not natively support 'until' in fetch_ohlcv,
                # so we pass params for the underlying Binance API.
                if until_ms is not None:
                    kwargs["params"] = {"endTime": until_ms}

                candles = self._exchange.fetch_ohlcv(**kwargs)

                if not candles:
                    break

                all_candles.extend(candles)

                # Check if we received a full page; if not, we're done.
                if len(candles) < page_limit:
                    break

                # Advance the cursor past the last candle.
                last_ts = candles[-1][0]
                if until_ms is not None and last_ts >= until_ms:
                    break

                current_since = last_ts + 1  # +1 ms to avoid duplicate

        except ccxt.NetworkError as exc:
            raise SourceUnavailableError("binance_spot", str(exc))
        except ccxt.ExchangeError as exc:
            logger.error(f"Binance exchange error: {exc}")
            # Return whatever we have so far rather than crashing.
        except Exception as exc:
            logger.error(f"Unexpected error fetching OHLCV: {exc}")

        if not all_candles:
            return self._empty_ohlcv()

        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")

        return self._normalise_df(df)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_ohlcv() -> pd.DataFrame:
        """Return an empty OHLCV DataFrame with the correct schema."""
        df = pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
        )
        df.index.name = "timestamp"
        return df
