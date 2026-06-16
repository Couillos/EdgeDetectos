"""
Vol Contraction Breakdown
Generated edge from formula engine.
Short: (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)) < (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)).shift(5) & close < ema(close, 20)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Vol_Contraction_Breakdown_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('(bb_upper(close, 20, 2) - bb_lower(close, 20, 2)) < (bb_upper(close, 20, 2) - bb_lower(close, 20, 2)).shift(5) & close < ema(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Vol Contraction Breakdown',
        entry_condition=Vol_Contraction_Breakdown_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Narrowing BB width with price below EMA signals coiling for downside breakdown.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

