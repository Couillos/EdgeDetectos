"""
market_data_manager — unified market data fetching, caching, and management.

Public API:
    MarketDataManager  — single entry point for all operations.
    Metric             — enum of supported data metrics.
    Request            — dataclass encapsulating a fetch request.
    CandleManager      — backward-compatible shim (wraps MarketDataManager).

Example::

    from candle_manager import MarketDataManager, Metric

    mdm = MarketDataManager()
    df = mdm.get(Metric.OHLCV, "BTC/USDT", "1h",
                 since="2024-01-01", until="2024-01-31")
    print(df.head())
"""

from .manager import MarketDataManager
from .models import Metric, Request
from .exceptions import (
    MarketDataError,
    InvalidMetricError,
    InvalidTimeframeError,
    InvalidSymbolError,
    SourceUnavailableError,
    RateLimitExhaustedError,
)

import pandas as pd
from pathlib import Path
from typing import Optional


class CandleManager:
    """
    Backward-compatible shim wrapping MarketDataManager.
    Provides the old get_candles() API using MarketDataManager internally.
    """
    def __init__(self, cache_dir: str = "./cache"):
        self._mdm = MarketDataManager(cache_dir=str(Path(cache_dir) / "market_data"))

    def get_candles(self, symbol: str, timeframe: str,
                    since: Optional[str] = None,
                    until: Optional[str] = None,
                    limit: Optional[int] = None,
                    force_refresh: bool = False) -> pd.DataFrame:
        return self._mdm.get(Metric.OHLCV, symbol, timeframe,
                             since=since, until=until,
                             limit=limit, force_refresh=force_refresh)

    def refresh_cache(self, symbol: str, timeframe: str):
        self._mdm.refresh_cache(Metric.OHLCV, symbol, timeframe)

    def clear_cache(self, symbol=None, timeframe=None):
        self._mdm.clear_cache(metric=Metric.OHLCV, symbol=symbol, timeframe=timeframe)

    def get_cache_info(self) -> pd.DataFrame:
        return self._mdm.cache_info()

    def get_available_symbols(self):
        return self._mdm.available_symbols(Metric.OHLCV)


__all__ = [
    "MarketDataManager",
    "Metric",
    "Request",
    "CandleManager",
    "MarketDataError",
    "InvalidMetricError",
    "InvalidTimeframeError",
    "InvalidSymbolError",
    "SourceUnavailableError",
    "RateLimitExhaustedError",
]

__version__ = "2.0.0"
