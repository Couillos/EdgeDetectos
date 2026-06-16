"""
End of Week Reversal
Generated edge from formula engine.
Short: dayofweek() == 5 & rsi(close, 14) > 70 & close > sma(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def End_of_Week_Reversal_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('dayofweek() == 5 & rsi(close, 14) > 70 & close > sma(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='End of Week Reversal',
        entry_condition=End_of_Week_Reversal_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Friday overbought above SMA captures tendency for weekend positioning unwinds.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

