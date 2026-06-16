"""
EMA Death Cross
Generated edge from formula engine.
Short: cross_below(ema(close, 9), ema(close, 21))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def EMA_Death_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cross_below(ema(close, 9), ema(close, 21))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='EMA Death Cross',
        entry_condition=EMA_Death_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Fast EMA crossing below slow EMA signals emerging downtrend momentum.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

