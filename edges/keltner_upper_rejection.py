"""
Keltner Upper Rejection
Generated edge from formula engine.
Short: close > keltner_upper(high, low, close, 20, 1.5) & rsi(close, 14) > 65
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Keltner_Upper_Rejection_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('close > keltner_upper(high, low, close, 20, 1.5) & rsi(close, 14) > 65', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Keltner Upper Rejection',
        entry_condition=Keltner_Upper_Rejection_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price above Keltner upper channel with elevated RSI indicates overbought reversion setup.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

