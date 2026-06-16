"""
OBV Bearish Divergence
Generated edge from formula engine.
Short: obv(close, volume) < obv(close, volume).shift(10) & close > close.shift(10)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def OBV_Bearish_Divergence_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('obv(close, volume) < obv(close, volume).shift(10) & close > close.shift(10)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='OBV Bearish Divergence',
        entry_condition=OBV_Bearish_Divergence_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Falling OBV with rising price reveals hidden distribution by smart money.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

