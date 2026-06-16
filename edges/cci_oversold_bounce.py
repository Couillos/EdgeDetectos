"""
CCI Oversold Bounce
Generated edge from formula engine.
Long: cci(high, low, close, 20) < -100 & cross_above(cci(high, low, close, 20), -100)
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def CCI_Oversold_Bounce_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cci(high, low, close, 20) < -100 & cross_above(cci(high, low, close, 20), -100)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='CCI Oversold Bounce',
        entry_condition=CCI_Oversold_Bounce_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='CCI crossing up from extreme oversold confirms momentum reversal from deep levels.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

