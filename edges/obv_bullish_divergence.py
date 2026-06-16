"""
OBV Bullish Divergence
Generated edge from formula engine.
Long: obv(close, volume) > obv(close, volume).shift(10) & close < close.shift(10)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def OBV_Bullish_Divergence_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('obv(close, volume) > obv(close, volume).shift(10) & close < close.shift(10)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='OBV Bullish Divergence',
        entry_condition=OBV_Bullish_Divergence_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Rising OBV with falling price reveals hidden accumulation by smart money.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

