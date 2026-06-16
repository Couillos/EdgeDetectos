"""
CCI Overbought Drop
Generated edge from formula engine.
Short: cci(high, low, close, 20) > 100 & cross_below(cci(high, low, close, 20), 100)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def CCI_Overbought_Drop_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('cci(high, low, close, 20) > 100 & cross_below(cci(high, low, close, 20), 100)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='CCI Overbought Drop',
        entry_condition=CCI_Overbought_Drop_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='CCI crossing down from extreme overbought confirms momentum reversal from high levels.',
        direction='short',
        metric='ohlcv',
        timeframe='1h',
    ))

