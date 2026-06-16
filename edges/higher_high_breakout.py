"""
Higher High Breakout
Generated edge from formula engine.
Long: higher_high(close, 5) & volume > volume.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Higher_High_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('higher_high(close, 5) & volume > volume.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Higher High Breakout',
        entry_condition=Higher_High_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='New higher high with volume confirmation signals breakout from consolidation.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

