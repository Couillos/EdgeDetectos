"""
Williams R Oversold
Generated edge from formula engine.
Long: williams_r(high, low, close, 14) < -80 & cross_above(williams_r(high, low, close, 14), -80)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Williams_R_Oversold_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('williams_r(high, low, close, 14) < -80 & cross_above(williams_r(high, low, close, 14), -80)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Williams R Oversold',
        entry_condition=Williams_R_Oversold_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Williams %R crossing up from oversold signals momentum shifting from extreme low.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

