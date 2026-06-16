"""
ATR Expansion Short
Generated edge from formula engine.
Short: atr(high, low, close, 14) > highest(atr(high, low, close, 14).shift(1), 10) & close < close.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def ATR_Expansion_Short_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('atr(high, low, close, 14) > highest(atr(high, low, close, 14).shift(1), 10) & close < close.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='ATR Expansion Short',
        entry_condition=ATR_Expansion_Short_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='ATR at 10-bar high with falling price confirms volatility-driven bearish expansion.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

