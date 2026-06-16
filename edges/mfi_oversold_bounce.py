"""
MFI Oversold Bounce
Generated edge from formula engine.
Long: mfi(high, low, close, 14) < 20 & cross_above(mfi(high, low, close, 14), 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def MFI_Oversold_Bounce_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('mfi(high, low, close, 14) < 20 & cross_above(mfi(high, low, close, 14), 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='MFI Oversold Bounce',
        entry_condition=MFI_Oversold_Bounce_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='MFI crossing up from extreme oversold signals volume-backed buying pressure returning.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

