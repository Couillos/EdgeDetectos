"""
Custom exception hierarchy for the market_data_manager package.

All domain-specific errors inherit from MarketDataError so callers can
catch the entire family with a single except clause, or target a specific
subclass when finer-grained handling is needed.
"""


class MarketDataError(Exception):
    """Base exception for all market data manager errors.

    Every custom exception in this package inherits from this class,
    enabling broad ``except MarketDataError`` handling at call sites.
    """

    def __init__(self, message: str = "", *args, **kwargs) -> None:
        self.message = message
        super().__init__(message, *args, **kwargs)

    def __str__(self) -> str:
        return self.message or super().__str__()


class InvalidMetricError(MarketDataError):
    """Raised when an unsupported or unrecognised metric is requested.

    Example:
        >>> raise InvalidMetricError("blah")
    """

    def __init__(self, metric: str) -> None:
        self.metric = metric
        super().__init__(f"Invalid or unsupported metric: '{metric}'")


class InvalidTimeframeError(MarketDataError):
    """Raised when a timeframe is not supported by the target source.

    Attributes:
        timeframe: The invalid timeframe string.
        exchange: The exchange that was queried.
        supported: List of valid timeframes for that exchange/metric pair.
    """

    def __init__(
        self,
        timeframe: str,
        exchange: str = "",
        supported: list[str] | None = None,
    ) -> None:
        self.timeframe = timeframe
        self.exchange = exchange
        self.supported = supported or []
        msg = f"Invalid timeframe '{timeframe}'"
        if exchange:
            msg += f" for {exchange}"
        if self.supported:
            msg += f". Supported: {self.supported}"
        super().__init__(msg)


class InvalidSymbolError(MarketDataError):
    """Raised when a symbol is not supported by the target source.

    Attributes:
        symbol: The invalid symbol string.
        exchange: The exchange that was queried.
    """

    def __init__(self, symbol: str, exchange: str = "") -> None:
        self.symbol = symbol
        self.exchange = exchange
        msg = f"Invalid or unsupported symbol: '{symbol}'"
        if exchange:
            msg += f" on {exchange}"
        super().__init__(msg)


class SourceUnavailableError(MarketDataError):
    """Raised when the data source (exchange API) cannot be reached.

    This typically wraps a ``requests.ConnectionError`` or HTTP 5xx response.
    """

    def __init__(self, source: str, detail: str = "") -> None:
        self.source = source
        msg = f"Source '{source}' is unavailable"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class RateLimitExhaustedError(MarketDataError):
    """Raised when the rate-limit budget is fully consumed and the caller
    does not want to wait.

    This is distinct from the *blocking* behaviour of ``RateLimiter.wait_if_needed``:
    it is used when a non-blocking check determines the budget is exhausted.
    """

    def __init__(self, exchange: str, retry_after: float = 0.0) -> None:
        self.exchange = exchange
        self.retry_after = retry_after
        msg = f"Rate limit exhausted for '{exchange}'"
        if retry_after > 0:
            msg += f". Retry after {retry_after:.1f}s"
        super().__init__(msg)
