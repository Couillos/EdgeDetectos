"""
Z-Score Deep Oversold
Generated edge from formula engine.
Long: zscore(close, 20) < -2.0 & close > close.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Z_Score_Deep_Oversold_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('zscore(close, 20) < -2.0 & close > close.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Z-Score Deep Oversold',
        entry_condition=Z_Score_Deep_Oversold_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Z-score beyond -2 with price starting to rise indicates statistical reversion in progress.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

