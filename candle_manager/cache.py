"""
Per-metric / per-symbol / per-timeframe pickle cache store.

Cache files are stored under ``cache_dir`` with the following layout::

    cache_dir/
    ├── ohlcv/
    │   ├── BTC_USDT_1h.pkl
    │   └── ETH_USDT_4h.pkl
    ├── funding_rate/
    │   └── BTC_USDT_8h.pkl
    ├── open_interest/
    │   └── BTC_USDT_1h.pkl
    ├── taker_volume/
    │   └── BTC_USDT_1h.pkl
    ├── long_short_ratio/
    │   └── BTC_USDT_5m.pkl
    ├── liquidations/
    │   └── BTC_USDT_1h.pkl
    └── liquidations_raw/
        └── BTC_USDT.pkl

All DataFrames use a ``DatetimeIndex`` named ``"timestamp"`` in UTC,
sorted ascending, with no duplicate indices.

Writes are atomic: data is serialised to a temporary file first, then
``os.replace()`` is used to swap it into place, preventing partial reads.
"""

from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger


class CacheStore:
    """File-backed pickle cache for market-data DataFrames.

    Args:
        cache_dir: Root directory for cache files.
    """

    def __init__(self, cache_dir: str = "./cache/market_data") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CacheStore initialised at {self._cache_dir}")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _metric_dir(self, metric: str) -> Path:
        """Return (and create) the subdirectory for a given metric."""
        d = self._cache_dir / metric
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _safe_symbol(symbol: str) -> str:
        """Replace ``/`` with ``_`` for safe filesystem paths."""
        return symbol.replace("/", "_")

    def _pkl_path(self, metric: str, symbol: str, timeframe: str) -> Path:
        """Full path to the cache pickle file.

        Args:
            metric: Metric value string, e.g. ``"ohlcv"``.
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.
            timeframe: Interval string, e.g. ``"1h"``.

        Returns:
            ``Path`` object for the cache file.
        """
        fname = f"{self._safe_symbol(symbol)}_{timeframe}.pkl"
        return self._metric_dir(metric) / fname

    def _raw_pkl_path(self, symbol: str) -> Path:
        """Path to the *raw* liquidations cache (no timeframe dimension).

        Args:
            symbol: Canonical symbol, e.g. ``"BTC/USDT"``.

        Returns:
            ``Path`` for the raw pickle file.
        """
        d = self._cache_dir / "liquidations_raw"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{self._safe_symbol(symbol)}.pkl"

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def load(
        self,
        metric: str,
        symbol: str,
        timeframe: str,
    ) -> Optional[pd.DataFrame]:
        """Load a cached DataFrame.

        Args:
            metric: Metric value string.
            symbol: Canonical symbol.
            timeframe: Interval string.

        Returns:
            The cached ``pd.DataFrame``, or ``None`` if the file is
            missing, corrupt, or otherwise unreadable.
        """
        path = self._pkl_path(metric, symbol, timeframe)
        return self._load_path(path)

    def load_raw(
        self,
        symbol: str,
    ) -> Optional[pd.DataFrame]:
        """Load the raw liquidations cache for *symbol*.

        Args:
            symbol: Canonical symbol.

        Returns:
            The raw ``pd.DataFrame`` or ``None``.
        """
        path = self._raw_pkl_path(symbol)
        return self._load_path(path)

    def save(
        self,
        df: pd.DataFrame,
        metric: str,
        symbol: str,
        timeframe: str,
    ) -> None:
        """Atomically persist a DataFrame to the cache.

        The write is performed in two stages:
        1. Serialise to a temporary file in the same directory.
        2. ``os.replace()`` the temp file onto the final path.

        This ensures no reader ever sees a partially-written file.

        Args:
            df: The DataFrame to cache.
            metric: Metric value string.
            symbol: Canonical symbol.
            timeframe: Interval string.
        """
        path = self._pkl_path(metric, symbol, timeframe)
        self._atomic_write(path, df)
        logger.debug(
            f"Cache saved: {path} ({len(df)} rows, "
            f"{df.index.min()} → {df.index.max()})"
        )

    def save_raw(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> None:
        """Save the raw liquidations DataFrame (no timeframe).

        Args:
            df: The raw DataFrame to cache.
            symbol: Canonical symbol.
        """
        path = self._raw_pkl_path(symbol)
        self._atomic_write(path, df)
        logger.debug(
            f"Raw cache saved: {path} ({len(df)} rows)"
        )

    def delete(
        self,
        metric: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> int:
        """Delete cache files matching the given criteria.

        Any criterion that is ``None`` acts as a wildcard.  For example,
        ``delete(metric="ohlcv")`` removes *all* OHLCV caches.

        Args:
            metric: Metric to match (or ``None`` for any).
            symbol: Symbol to match (or ``None`` for any).
            timeframe: Timeframe to match (or ``None`` for any).

        Returns:
            The number of files deleted.
        """
        deleted = 0

        # Determine which metric subdirectories to scan.
        if metric is not None:
            metric_dirs = [self._cache_dir / metric]
        else:
            metric_dirs = [
                p for p in self._cache_dir.iterdir()
                if p.is_dir() and p.name != "liquidations_raw"
            ]

        for mdir in metric_dirs:
            if not mdir.is_dir():
                continue
            for pkl in mdir.glob("*.pkl"):
                if self._pkl_matches(pkl, symbol, timeframe):
                    pkl.unlink()
                    deleted += 1
                    logger.debug(f"Cache deleted: {pkl}")

        # Also handle liquidations_raw if metric is None or "liquidations".
        if metric is None or metric == "liquidations":
            raw_dir = self._cache_dir / "liquidations_raw"
            if raw_dir.is_dir():
                for pkl in raw_dir.glob("*.pkl"):
                    if symbol is not None:
                        expected = f"{self._safe_symbol(symbol)}.pkl"
                        if pkl.name != expected:
                            continue
                    pkl.unlink()
                    deleted += 1
                    logger.debug(f"Raw cache deleted: {pkl}")

        logger.info(f"Cache cleared: {deleted} file(s) deleted")
        return deleted

    def info(self) -> pd.DataFrame:
        """Scan all cache files and return metadata as a DataFrame.

        Returns:
            A ``pd.DataFrame`` with columns:
            ``metric``, ``symbol``, ``timeframe``, ``rows``,
            ``earliest``, ``latest``, ``size_kb``.
        """
        rows: list[dict] = []

        for mdir in sorted(self._cache_dir.iterdir()):
            if not mdir.is_dir():
                continue

            metric_name = mdir.name

            for pkl in sorted(mdir.glob("*.pkl")):
                info = self._pkl_metadata(pkl, metric_name)
                if info is not None:
                    rows.append(info)

        if not rows:
            return pd.DataFrame(
                columns=[
                    "metric", "symbol", "timeframe",
                    "rows", "earliest", "latest", "size_kb",
                ]
            )

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_path(self, path: Path) -> Optional[pd.DataFrame]:
        """Load a pickle file, returning None on any failure."""
        if not path.exists():
            return None
        try:
            with open(path, "rb") as fh:
                df = pickle.load(fh)
            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Cache {path} does not contain a DataFrame")
                return None
            return df
        except Exception as exc:
            logger.warning(f"Cache {path} is corrupt or unreadable: {exc}")
            return None

    def _atomic_write(self, path: Path, df: pd.DataFrame) -> None:
        """Write *df* to *path* via a temporary file + ``os.replace``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Write to a temporary file in the *same* directory so that
            # os.replace is atomic on the same filesystem.
            fd, tmp_path = tempfile.mkstemp(
                suffix=".tmp",
                dir=str(path.parent),
            )
            try:
                with os.fdopen(fd, "wb") as fh:
                    pickle.dump(df, fh, protocol=pickle.HIGHEST_PROTOCOL)
                os.replace(tmp_path, str(path))
            except BaseException:
                # Clean up the temp file on any error.
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as exc:
            logger.error(f"Failed to write cache {path}: {exc}")
            raise

    @staticmethod
    def _pkl_matches(
        pkl: Path,
        symbol: Optional[str],
        timeframe: Optional[str],
    ) -> bool:
        """Check whether a cache file path matches the given filters.

        File names follow the pattern ``{SYMBOL}_{TIMEFRAME}.pkl``
        where SYMBOL uses ``_`` instead of ``/``.
        """
        stem = pkl.stem  # e.g. "BTC_USDT_1h"
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            return False

        file_symbol, file_timeframe = parts

        if symbol is not None:
            safe = symbol.replace("/", "_")
            if file_symbol != safe:
                return False

        if timeframe is not None:
            if file_timeframe != timeframe:
                return False

        return True

    def _pkl_metadata(
        self, pkl: Path, metric_name: str
    ) -> Optional[dict]:
        """Extract metadata from a single pickle file."""
        try:
            size_kb = pkl.stat().st_size / 1024
            df = self._load_path(pkl)
            if df is None or df.empty:
                return {
                    "metric": metric_name,
                    "symbol": pkl.stem.rsplit("_", 1)[0].replace("_", "/"),
                    "timeframe": pkl.stem.rsplit("_", 1)[1] if "_" in pkl.stem else "",
                    "rows": 0,
                    "earliest": pd.NaT,
                    "latest": pd.NaT,
                    "size_kb": round(size_kb, 1),
                }

            # Parse symbol and timeframe from filename.
            stem = pkl.stem
            parts = stem.rsplit("_", 1)
            file_symbol = parts[0].replace("_", "/") if len(parts) == 2 else stem
            file_timeframe = parts[1] if len(parts) == 2 else ""

            # Special case for liquidations_raw — no timeframe in filename.
            if metric_name == "liquidations_raw":
                file_symbol = stem.replace("_", "/")
                file_timeframe = ""

            return {
                "metric": metric_name,
                "symbol": file_symbol,
                "timeframe": file_timeframe,
                "rows": len(df),
                "earliest": df.index.min(),
                "latest": df.index.max(),
                "size_kb": round(size_kb, 1),
            }
        except Exception as exc:
            logger.warning(f"Could not read metadata for {pkl}: {exc}")
            return None
