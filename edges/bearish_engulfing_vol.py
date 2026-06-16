"""
Bearish Engulfing Vol
Generated edge from formula engine.
Short: engulfing_bear(open, close) & volume > volume.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Bearish_Engulfing_Vol_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('engulfing_bear(open, close) & volume > volume.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Bearish Engulfing Vol',
        entry_condition=Bearish_Engulfing_Vol_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Bearish engulfing candle with volume confirmation signals strong reversal pattern.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

