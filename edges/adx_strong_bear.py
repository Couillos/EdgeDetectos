"""
ADX Strong Bear
Generated edge from formula engine.
Short: adx(high, low, close, 14) > 25 & adx_neg(high, low, close, 14) > adx_pos(high, low, close, 14)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def ADX_Strong_Bear_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('adx(high, low, close, 14) > 25 & adx_neg(high, low, close, 14) > adx_pos(high, low, close, 14)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='ADX Strong Bear',
        entry_condition=ADX_Strong_Bear_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Strong ADX with negative directional indicator dominant confirms robust downtrend.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

