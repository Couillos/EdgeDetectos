"""
Funding Extreme Neg
Generated edge from formula engine.
Long: funding_rate < -0.001 & rsi(close, 14) < 35
Metric: funding_rate, Timeframe: 8h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Funding_Extreme_Neg_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('funding_rate < -0.001 & rsi(close, 14) < 35', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Funding Extreme Neg',
        entry_condition=Funding_Extreme_Neg_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Deeply negative funding with oversold RSI signals crowded short side ripe for squeeze.',
        direction='long',
        metric='funding_rate',
        timeframe='8h',
    ))

