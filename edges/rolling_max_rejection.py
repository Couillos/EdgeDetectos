"""
Rolling Max Rejection
Generated edge from formula engine.
Short: close >= rolling_max(close, 20) * 0.99 & rsi(close, 14) > 70
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Rolling_Max_Rejection_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close >= rolling_max(close, 20) * 0.99 & rsi(close, 14) > 70', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Rolling Max Rejection',
        entry_condition=Rolling_Max_Rejection_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price near 20-bar rolling maximum with overbought RSI signals statistical ceiling test.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

