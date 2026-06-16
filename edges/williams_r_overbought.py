"""
Williams R Overbought
Generated edge from formula engine.
Short: williams_r(high, low, close, 14) > -20 & cross_below(williams_r(high, low, close, 14), -20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Williams_R_Overbought_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('williams_r(high, low, close, 14) > -20 & cross_below(williams_r(high, low, close, 14), -20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Williams R Overbought',
        entry_condition=Williams_R_Overbought_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Williams %R crossing down from overbought signals momentum shifting from extreme high.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

