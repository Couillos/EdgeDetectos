"""
BB Upper Rejection
Generated edge from formula engine.
Short: close > bb_upper(close, 20, 2) & rsi(close, 14) > 70
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def BB_Upper_Rejection_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close > bb_upper(close, 20, 2) & rsi(close, 14) > 70', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='BB Upper Rejection',
        entry_condition=BB_Upper_Rejection_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price above upper Bollinger Band with overbought RSI signals overextension likely to revert.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

