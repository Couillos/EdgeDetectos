"""
Donchian Breakout Up
Generated edge from formula engine.
Long: cross_above(close, donchian_upper(high, low, 20))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Donchian_Breakout_Up_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(close, donchian_upper(high, low, 20))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Donchian Breakout Up',
        entry_condition=Donchian_Breakout_Up_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price breaking above Donchian upper channel signals range expansion breakout.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

