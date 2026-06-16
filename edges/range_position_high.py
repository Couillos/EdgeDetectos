"""
Range Position High
Generated edge from formula engine.
Short: (close - lowest(close, 20)) / (highest(close, 20) - lowest(close, 20)) > 0.9
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Range_Position_High_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('(close - lowest(close, 20)) / (highest(close, 20) - lowest(close, 20)) > 0.9', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Range Position High',
        entry_condition=Range_Position_High_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price in top 10% of 20-bar range signals statistical extreme positioning.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

