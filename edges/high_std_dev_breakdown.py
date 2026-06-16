"""
High Std Dev Breakdown
Generated edge from formula engine.
Short: rolling_std(close, 20) > rolling_std(close, 20).shift(5) & close < sma(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def High_Std_Dev_Breakdown_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('rolling_std(close, 20) > rolling_std(close, 20).shift(5) & close < sma(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='High Std Dev Breakdown',
        entry_condition=High_Std_Dev_Breakdown_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Rising volatility with price below mean signals expanding downside risk.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

