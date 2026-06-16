"""
SMA Trend Continuation
Generated edge from formula engine.
Long: close > sma(close, 50) & cross_above(close, sma(close, 20))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def SMA_Trend_Continuation_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close > sma(close, 50) & cross_above(close, sma(close, 20))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='SMA Trend Continuation',
        entry_condition=SMA_Trend_Continuation_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price above 50-SMA and crossing back above 20-SMA confirms trend continuation.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

