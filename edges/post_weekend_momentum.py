"""
Post Weekend Momentum
Generated edge from formula engine.
Long: dayofweek() == 1 & close > close.shift(24) & rsi(close, 14) > 50
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Post_Weekend_Momentum_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('dayofweek() == 1 & close > close.shift(24) & rsi(close, 14) > 50', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Post Weekend Momentum',
        entry_condition=Post_Weekend_Momentum_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Monday gap-up from Friday close with bullish RSI captures weekend drift tendency.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

