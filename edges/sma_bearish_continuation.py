"""
SMA Bearish Continuation
Generated edge from formula engine.
Short: close < sma(close, 50) & cross_below(close, sma(close, 20))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def SMA_Bearish_Continuation_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close < sma(close, 50) & cross_below(close, sma(close, 20))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='SMA Bearish Continuation',
        entry_condition=SMA_Bearish_Continuation_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price below 50-SMA and crossing below 20-SMA confirms bearish trend continuation.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

