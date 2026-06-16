"""
Green Surge Volume
Generated edge from formula engine.
Long: consecutive_green(2) & volume > volume.shift(1) * 1.5
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Green_Surge_Volume_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('consecutive_green(2) & volume > volume.shift(1) * 1.5', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Green Surge Volume',
        entry_condition=Green_Surge_Volume_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Back-to-back green candles with surging volume signals aggressive buying pressure.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

