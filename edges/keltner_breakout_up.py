"""
Keltner Breakout Up
Generated edge from formula engine.
Long: cross_above(close, keltner_upper(high, low, close, 20, 2))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Keltner_Breakout_Up_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(close, keltner_upper(high, low, close, 20, 2))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Keltner Breakout Up',
        entry_condition=Keltner_Breakout_Up_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price breaking above Keltner upper channel signals volatility expansion with bullish momentum.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

