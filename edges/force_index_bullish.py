"""
Force Index Bullish
Generated edge from formula engine.
Long: cross_above(force_index(close, volume, 13), 0) & close > ema(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Force_Index_Bullish_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(force_index(close, volume, 13), 0) & close > ema(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Force Index Bullish',
        entry_condition=Force_Index_Bullish_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Force Index crossing above zero with price above EMA confirms volume-backed strength.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

