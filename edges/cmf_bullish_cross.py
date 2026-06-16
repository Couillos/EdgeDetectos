"""
CMF Bullish Cross
Generated edge from formula engine.
Long: cross_above(cmf(high, low, close, 20), 0)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def CMF_Bullish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(cmf(high, low, close, 20), 0)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='CMF Bullish Cross',
        entry_condition=CMF_Bullish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Chaikin Money Flow crossing above zero signals shift from distribution to accumulation.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

