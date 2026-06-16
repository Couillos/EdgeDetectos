"""
Aroon Up Breakout
Generated edge from formula engine.
Long: aroon_up(high, low, 25) > 90 & adx(high, low, close, 14) > 20
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Aroon_Up_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('aroon_up(high, low, 25) > 90 & adx(high, low, close, 14) > 20', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Aroon Up Breakout',
        entry_condition=Aroon_Up_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Aroon Up above 90 with confirming ADX signals strong new high trend momentum.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

