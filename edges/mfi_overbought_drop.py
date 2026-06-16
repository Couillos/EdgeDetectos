"""
MFI Overbought Drop
Generated edge from formula engine.
Short: mfi(high, low, close, 14) > 80 & cross_below(mfi(high, low, close, 14), 80)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def MFI_Overbought_Drop_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('mfi(high, low, close, 14) > 80 & cross_below(mfi(high, low, close, 14), 80)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='MFI Overbought Drop',
        entry_condition=MFI_Overbought_Drop_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='MFI crossing down from extreme overbought signals volume-backed selling pressure returning.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

