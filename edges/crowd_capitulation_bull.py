"""
Crowd Capitulation Bull
Generated edge from formula engine.
Long: funding_rate < -0.0005 & volume > volume.shift(1) * 2
Metric: funding_rate, Timeframe: 8h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Crowd_Capitulation_Bull_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for long signal, 0 otherwise."""
    return eval_formula('funding_rate < -0.0005 & volume > volume.shift(1) * 2', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Crowd Capitulation Bull',
        entry_condition=Crowd_Capitulation_Bull_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Negative funding with volume spike signals capitulation event and potential bottom.',
        direction='long',
        metric='funding_rate',
        timeframe='8h',
    ))

