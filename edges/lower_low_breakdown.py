"""
Lower Low Breakdown
Generated edge from formula engine.
Short: lower_low(close, 5) & volume > volume.shift(1)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Lower_Low_Breakdown_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('lower_low(close, 5) & volume > volume.shift(1)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Lower Low Breakdown',
        entry_condition=Lower_Low_Breakdown_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='New lower low with volume confirmation signals breakdown from support.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

