"""
Range Position Low
Generated edge from formula engine.
Long: (close - lowest(close, 20)) / (highest(close, 20) - lowest(close, 20)) < 0.1
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Range_Position_Low_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('(close - lowest(close, 20)) / (highest(close, 20) - lowest(close, 20)) < 0.1', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Range Position Low',
        entry_condition=Range_Position_Low_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price in bottom 10% of 20-bar range signals statistical extreme positioning.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

