"""
US Session Momentum
Generated edge from formula engine.
Long: hour() == 14 & close > sma(close, 20) & rsi(close, 14) > 55
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def US_Session_Momentum_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('hour() == 14 & close > sma(close, 20) & rsi(close, 14) > 55', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='US Session Momentum',
        entry_condition=US_Session_Momentum_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='US session open with price above SMA captures American session momentum tendency.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

