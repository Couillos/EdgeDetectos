"""
EMA Golden Cross
Generated edge from formula engine.
Long: cross_above(ema(close, 9), ema(close, 21))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def EMA_Golden_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(ema(close, 9), ema(close, 21))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='EMA Golden Cross',
        entry_condition=EMA_Golden_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Fast EMA crossing above slow EMA signals emerging uptrend momentum.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

