"""
Percentile Bottom
Generated edge from formula engine.
Long: percentile(close, 50) < 10
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Percentile_Bottom_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('percentile(close, 50) < 10', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Percentile Bottom',
        entry_condition=Percentile_Bottom_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price in bottom 10th percentile of 50-bar range signals statistical extreme likely to revert.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

