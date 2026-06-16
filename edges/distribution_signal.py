"""
Distribution Signal
Generated edge from formula engine.
Short: acc_dist_index(high, low, close, volume) < acc_dist_index(high, low, close, volume).shift(5) & close > close.shift(5)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Distribution_Signal_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('acc_dist_index(high, low, close, volume) < acc_dist_index(high, low, close, volume).shift(5) & close > close.shift(5)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Distribution Signal',
        entry_condition=Distribution_Signal_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Falling A/D line with rising price reveals stealth distribution phase.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

