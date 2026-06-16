"""
Z-Score Deep Overbought
Generated edge from formula engine.
Short: zscore(close, 20) > 2.0 & close < close.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Z_Score_Deep_Overbought_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('zscore(close, 20) > 2.0 & close < close.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Z-Score Deep Overbought',
        entry_condition=Z_Score_Deep_Overbought_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Z-score beyond +2 with price starting to fall indicates statistical reversion underway.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

