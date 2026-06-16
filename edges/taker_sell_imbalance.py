"""
Taker Sell Imbalance
Generated edge from formula engine.
Short: taker_sell_ratio > 0.6 & close < ema(close, 20)
Metric: taker_volume, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Taker_Sell_Imbalance_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('taker_sell_ratio > 0.6 & close < ema(close, 20)', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Taker Sell Imbalance',
        entry_condition=Taker_Sell_Imbalance_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Dominant taker selling with price below EMA confirms aggressive supply conviction.',
        direction='short',
        metric='taker_volume',
        timeframe='1h',
    ))

