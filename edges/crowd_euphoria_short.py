"""
Crowd Euphoria Short
Generated edge from formula engine.
Short: funding_rate > 0.0005 & volume > volume.shift(1) * 2
Metric: funding_rate, Timeframe: 8h
"""

import pandas as pd
import numpy as np
from formula_engine import eval_formula


def Crowd_Euphoria_Short_condition(df: pd.DataFrame) -> pd.Series:
    """Return 1 for short signal, 0 otherwise."""
    return -eval_formula('funding_rate > 0.0005 & volume > volume.shift(1) * 2', df)


def register():
    from backtest import register_edge, Edge
    register_edge(Edge(
        name='Crowd Euphoria Short',
        entry_condition=Crowd_Euphoria_Short_condition,
        close_horizons=[1, 4, 6, 12, 24, 48, 72, 168],
        description='Positive funding with volume spike signals euphoria event and potential top.',
        direction='short',
        metric='funding_rate',
        timeframe='8h',
    ))

