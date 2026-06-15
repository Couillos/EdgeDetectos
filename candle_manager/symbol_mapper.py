"""
Cross-exchange symbol format resolution.

Users always interact with the *canonical* format ``"BASE/QUOTE"`` (e.g.
``"BTC/USDT"``).  Each exchange has its own idiosyncratic representation,
so this module provides bidirectional conversion.

Supported exchanges and their formats:
- ``binance_spot``  : ``"BTC/USDT"`` (ccxt handles the mapping transparently)
- ``binance_futures``: ``"BTCUSDT"`` (no separator)
- ``bybit``         : ``"BTCUSDT"`` (no separator)
- ``deribit``       : ``"BTC-PERPETUAL"``, ``"ETH-PERPETUAL"`` (only perpetuals)
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional

from loguru import logger

from .exceptions import InvalidSymbolError


class SymbolMapper:
    """Bidirectional symbol-format converter for supported exchanges.

    The canonical format is always ``"BASE/QUOTE"`` (upper-case).  Internal
    mappings are defined per-exchange so that ``to_exchange()`` produces the
    format the exchange API expects, and ``from_exchange()`` converts back.
    """

    # Canonical symbols that are broadly supported across exchanges.
    _CANONICAL_SYMBOLS: FrozenSet[str] = frozenset(
        {
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
            "XRP/USDT", "ADA/USDT", "DOGE/USDT", "DOT/USDT",
            "MATIC/USDT", "LTC/USDT", "AVAX/USDT", "LINK/USDT",
            "UNI/USDT", "ATOM/USDT", "ETC/USDT", "NEAR/USDT",
            "FIL/USDT", "APT/USDT", "ARB/USDT", "OP/USDT",
            "SHIB/USDT", "IMX/USDT", "RUNE/USDT", "AAVE/USDT",
            "SAND/USDT", "MANA/USDT", "CRV/USDT", "MKR/USDT",
            "SNX/USDT", "COMP/USDT",
        }
    )

    # Deribit only supports BTC and ETH perpetuals.
    _DERIBIT_SYMBOLS: Dict[str, str] = {
        "BTC/USDT": "BTC-PERPETUAL",
        "ETH/USDT": "ETH-PERPETUAL",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def to_exchange(symbol: str, exchange: str) -> str:
        """Convert a canonical symbol to the exchange-specific format.

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            exchange: Target exchange identifier.

        Returns:
            The exchange-formatted symbol string.

        Raises:
            InvalidSymbolError: If the symbol is not supported on the
                given exchange.
        """
        if not SymbolMapper.is_supported(symbol, exchange):
            raise InvalidSymbolError(symbol, exchange)

        if exchange == "binance_spot":
            # ccxt accepts "BTC/USDT" directly.
            return symbol

        if exchange == "binance_futures":
            # "BTC/USDT" → "BTCUSDT"
            return symbol.replace("/", "")

        if exchange == "bybit":
            # "BTC/USDT" → "BTCUSDT"
            return symbol.replace("/", "")

        if exchange == "deribit":
            mapped = SymbolMapper._DERIBIT_SYMBOLS.get(symbol)
            if mapped is not None:
                return mapped
            raise InvalidSymbolError(symbol, exchange)

        raise InvalidSymbolError(symbol, exchange)

    @staticmethod
    def from_exchange(symbol: str, exchange: str) -> str:
        """Convert an exchange-formatted symbol back to canonical format.

        Args:
            symbol: Exchange-specific symbol string.
            exchange: Source exchange identifier.

        Returns:
            The canonical symbol string, e.g. ``"BTC/USDT"``.

        Raises:
            InvalidSymbolError: If the symbol cannot be mapped.
        """
        if exchange == "binance_spot":
            # ccxt returns "BTC/USDT" already.
            if "/" in symbol:
                return symbol
            # Attempt to infer — unlikely path but defensive.
            return _infer_canonical(symbol)

        if exchange in ("binance_futures", "bybit"):
            # "BTCUSDT" → "BTC/USDT"
            if "/" in symbol:
                return symbol
            return _infer_canonical(symbol)

        if exchange == "deribit":
            # Reverse lookup: "BTC-PERPETUAL" → "BTC/USDT"
            for canonical, deribit_sym in SymbolMapper._DERIBIT_SYMBOLS.items():
                if deribit_sym == symbol:
                    return canonical
            raise InvalidSymbolError(symbol, exchange)

        raise InvalidSymbolError(symbol, exchange)

    @staticmethod
    def is_supported(symbol: str, exchange: str) -> bool:
        """Check whether *symbol* is supported on *exchange*.

        Args:
            symbol: Canonical symbol string.
            exchange: Exchange identifier.

        Returns:
            ``True`` if the symbol is supported.
        """
        if exchange == "deribit":
            return symbol in SymbolMapper._DERIBIT_SYMBOLS
        return symbol in SymbolMapper._CANONICAL_SYMBOLS

    @staticmethod
    def supported_symbols(exchange: str) -> list[str]:
        """Return the list of canonical symbols supported on *exchange*.

        Args:
            exchange: Exchange identifier.

        Returns:
            Sorted list of canonical symbol strings.
        """
        if exchange == "deribit":
            return sorted(SymbolMapper._DERIBIT_SYMBOLS.keys())
        return sorted(SymbolMapper._CANONICAL_SYMBOLS)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

# Common quote currencies to try when splitting an exchange symbol.
_QUOTE_CURRENCIES = ["USDT", "BUSD", "USDC", "BTC", "ETH", "BNB"]


def _infer_canonical(raw: str) -> str:
    """Attempt to convert a plain symbol like ``'BTCUSDT'`` to ``'BTC/USDT'``.

    This tries each known quote currency as a suffix split-point.

    Args:
        raw: Exchange symbol without a ``/`` separator.

    Returns:
        Canonical ``"BASE/QUOTE"`` string.

    Raises:
        InvalidSymbolError: If no known quote suffix matches.
    """
    for quote in _QUOTE_CURRENCIES:
        if raw.endswith(quote):
            base = raw[: -len(quote)]
            if base:  # non-empty base
                canonical = f"{base}/{quote}"
                logger.debug(f"Inferred canonical symbol: {raw} → {canonical}")
                return canonical
    raise InvalidSymbolError(raw, "(unknown exchange)")
