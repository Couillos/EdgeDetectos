"""
Funding Extreme Pos
Generated edge from formula engine.
Short: funding_rate > 0.001 & rsi(close, 14) > 65
Metric: funding_rate, Timeframe: 8h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Funding_Extreme_Pos_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('funding_rate > 0.001 & rsi(close, 14) > 65', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Funding Extreme Pos',
        entry_condition=Funding_Extreme_Pos_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Deeply positive funding with overbought RSI signals crowded long side ripe for dump.',
        direction='short',
        metric='funding_rate',
        timeframe='8h',
    ))

