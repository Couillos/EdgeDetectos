"""
RSI Deep Overbought
Generated edge from formula engine.
Short: rsi(close, 14) > 75 & cross_below(rsi(close, 14), 75)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def RSI_Deep_Overbought_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('rsi(close, 14) > 75 & cross_below(rsi(close, 14), 75)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='RSI Deep Overbought',
        entry_condition=RSI_Deep_Overbought_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='RSI crossing down from extreme overbought signals euphoria exhaustion and impending drop.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

