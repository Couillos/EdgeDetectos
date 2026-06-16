"""
PPO Bullish Cross
Generated edge from formula engine.
Long: cross_above(ppo(close, 12, 26), ppo_signal(close, 12, 26, 9))
Metric: ohlcv, Timeframe: 1h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def PPO_Bullish_Cross_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('cross_above(ppo(close, 12, 26), ppo_signal(close, 12, 26, 9))', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='PPO Bullish Cross',
        entry_condition=PPO_Bullish_Cross_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='PPO crossing its signal line confirms percentage-based momentum turning bullish.',
        direction='long',
        metric='ohlcv',
        timeframe='1h',
    ))

