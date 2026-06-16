"""
BB Breakout Up
Generated edge from formula engine.
Long: cross_above(close, bb_upper(close, 20, 2)) & atr(high, low, close, 14) > atr(high, low, close, 14).shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def BB_Breakout_Up_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(close, bb_upper(close, 20, 2)) & atr(high, low, close, 14) > atr(high, low, close, 14).shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='BB Breakout Up',
        entry_condition=BB_Breakout_Up_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price breaking above upper BB with expanding ATR signals volatility breakout to upside.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

