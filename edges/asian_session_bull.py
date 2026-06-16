"""
Asian Session Bull
Generated edge from formula engine.
Long: hour() >= 0 & hour() < 8 & close > ema(close, 20) & volume > volume.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Asian_Session_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('hour() >= 0 & hour() < 8 & close > ema(close, 20) & volume > volume.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Asian Session Bull',
        entry_condition=Asian_Session_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Asian session price above EMA with rising volume captures timezone-specific momentum.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

