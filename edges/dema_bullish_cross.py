"""
DEMA Bullish Cross
Generated edge from formula engine.
Long: cross_above(dema(close, 9), dema(close, 21))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def DEMA_Bullish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(dema(close, 9), dema(close, 21))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='DEMA Bullish Cross',
        entry_condition=DEMA_Bullish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Double EMA golden cross provides lower-lag trend confirmation signal.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

