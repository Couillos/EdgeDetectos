"""
Percentile Top
Generated edge from formula engine.
Short: percentile(close, 50) > 90
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Percentile_Top_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('percentile(close, 50) > 90', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Percentile Top',
        entry_condition=Percentile_Top_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Price in top 10th percentile of 50-bar range signals statistical extreme likely to revert.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

