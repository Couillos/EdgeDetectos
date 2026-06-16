"""
LS Contrarian Bear
Generated edge from formula engine.
Short: ls_ratio > 1.2 & rsi(close, 14) > 65
Metric: long_short_ratio, Timeframe: 4h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def LS_Contrarian_Bear_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('ls_ratio > 1.2 & rsi(close, 14) > 65', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='LS Contrarian Bear',
        entry_condition=LS_Contrarian_Bear_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Extreme long/short ratio favoring longs with overbought RSI signals contrarian short opportunity.',
        direction='short',
        metric='long_short_ratio',
        timeframe='4h',
    ))

