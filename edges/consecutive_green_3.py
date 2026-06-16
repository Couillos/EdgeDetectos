"""
Consecutive Green 3
Generated edge from formula engine.
Long: consecutive_green(3) & macd_hist(close, 12, 26, 9) > 0
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Consecutive_Green_3_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('consecutive_green(3) & macd_hist(close, 12, 26, 9) > 0', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Consecutive Green 3',
        entry_condition=Consecutive_Green_3_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Three consecutive green candles with positive MACD histogram confirms momentum surge.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

