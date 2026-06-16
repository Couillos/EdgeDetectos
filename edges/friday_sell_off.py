"""
Friday Sell Off
Generated edge from formula engine.
Short: dayofweek() == 5 & close < sma(close, 20) & rsi(close, 14) < 50
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Friday_Sell_Off_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('dayofweek() == 5 & close < sma(close, 20) & rsi(close, 14) < 50', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Friday Sell Off',
        entry_condition=Friday_Sell_Off_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Friday price below SMA with bearish RSI captures weekend risk-off tendency.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

