"""
RSI Deep Oversold
Generated edge from formula engine.
Long: cross_above(rsi(close, 14), 25)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def RSI_Deep_Oversold_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(rsi(close, 14), 25)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='RSI Deep Oversold',
        entry_condition=RSI_Deep_Oversold_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='RSI crossing up from extreme oversold signals capitulation exhaustion and impending bounce.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

