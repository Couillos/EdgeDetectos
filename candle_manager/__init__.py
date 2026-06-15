"""
market_data_manager — unified market data fetching, caching, and management.

Public API:
    MarketDataManager  — single entry point for all operations.
    Metric             — enum of supported data metrics.
    Request            — dataclass encapsulating a fetch request.

Example::

    from market_data_manager import MarketDataManager, Metric

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

__all__ = [
    "MarketDataManager",
    "Metric",
    "Request",
    "MarketDataError",
    "InvalidMetricError",
    "InvalidTimeframeError",
    "InvalidSymbolError",
    "SourceUnavailableError",
    "RateLimitExhaustedError",
]

__version__ = "2.0.0"
