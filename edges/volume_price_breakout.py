"""
Volume Price Breakout
Generated edge from formula engine.
Long: volume > volume.shift(1) * 1.5 & close > close.shift(1) & close > ema(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Volume_Price_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('volume > volume.shift(1) * 1.5 & close > close.shift(1) & close > ema(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Volume Price Breakout',
        entry_condition=Volume_Price_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='High volume breakout above EMA confirms genuine demand-driven price advance.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

