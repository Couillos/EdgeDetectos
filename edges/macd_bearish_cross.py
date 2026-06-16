"""
MACD Bearish Cross
Generated edge from formula engine.
Short: cross_below(macd(close, 12, 26), macd_signal(close, 12, 26, 9))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def MACD_Bearish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cross_below(macd(close, 12, 26), macd_signal(close, 12, 26, 9))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='MACD Bearish Cross',
        entry_condition=MACD_Bearish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='MACD line crossing below signal line confirms bearish momentum shift.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

