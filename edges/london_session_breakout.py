"""
London Session Breakout
Generated edge from formula engine.
Long: hour() == 8 & close > close.shift(4) & volume > volume.shift(4)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def London_Session_Breakout_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('hour() == 8 & close > close.shift(4) & volume > volume.shift(4)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='London Session Breakout',
        entry_condition=London_Session_Breakout_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='London open with rising price and volume captures European session breakout pattern.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

