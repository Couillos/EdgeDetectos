"""
LS Contrarian Bull
Generated edge from formula engine.
Long: ls_ratio < 0.8 & rsi(close, 14) < 35
Metric: long_short_ratio, Timeframe: 4h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def LS_Contrarian_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('ls_ratio < 0.8 & rsi(close, 14) < 35', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='LS Contrarian Bull',
        entry_condition=LS_Contrarian_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Extreme long/short ratio favoring shorts with oversold RSI signals contrarian long opportunity.',
        direction='long',
        metric='long_short_ratio',
        timeframe='4h',
    ))

