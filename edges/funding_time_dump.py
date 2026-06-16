"""
Funding Time Dump
Generated edge from formula engine.
Short: hour() == 0 & close < close.shift(4) & rsi(close, 14) < 45
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Funding_Time_Dump_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('hour() == 0 & close < close.shift(4) & rsi(close, 14) < 45', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Funding Time Dump',
        entry_condition=Funding_Time_Dump_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Midnight UTC with falling price captures funding-rate-time selling pressure.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

