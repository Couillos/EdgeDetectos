"""
OI Divergence Bull
Generated edge from formula engine.
Long: close < close.shift(10) & open_interest_usd > open_interest_usd.shift(10)
Metric: open_interest, Timeframe: 4h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def OI_Divergence_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('close < close.shift(10) & open_interest_usd > open_interest_usd.shift(10)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='OI Divergence Bull',
        entry_condition=OI_Divergence_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Rising open interest with falling price indicates new longs entering, suggesting reversal.',
        direction='long',
        metric='open_interest',
        timeframe='4h',
    ))

