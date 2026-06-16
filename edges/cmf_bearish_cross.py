"""
CMF Bearish Cross
Generated edge from formula engine.
Short: cross_below(cmf(high, low, close, 20), 0)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def CMF_Bearish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cross_below(cmf(high, low, close, 20), 0)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='CMF Bearish Cross',
        entry_condition=CMF_Bearish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Chaikin Money Flow crossing below zero signals shift from accumulation to distribution.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

