"""
US Session Sell
Generated edge from formula engine.
Short: hour() == 15 & close < close.shift(4) & macd_hist(close, 12, 26, 9) < 0
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def US_Session_Sell_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('hour() == 15 & close < close.shift(4) & macd_hist(close, 12, 26, 9) < 0', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='US Session Sell',
        entry_condition=US_Session_Sell_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='US afternoon with falling price and bearish MACD captures late-session sell tendency.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

