"""
Edge Registry
=============
Shared registry for edge definitions.
Separated from backtest.py to avoid __main__ vs backtest module conflicts.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

Signal = int  # 1=LONG, -1=SHORT, 0=NEUTRAL
ConditionFn = Callable[[pd.DataFrame], pd.Series]


_registry: Dict[str, 'Edge'] = {}


@dataclass
class Edge:
    name: str
    entry_condition: ConditionFn
    close_horizons: List[int] = field(default_factory=lambda: [1, 2, 4, 8, 12, 24])
    color: str = '#2196F3'
    description: str = ''


def register_edge(edge: Edge):
    _registry[edge.name] = edge
    return edge


def get_edge(name: str) -> Optional[Edge]:
    return _registry.get(name)


def list_edges() -> List[str]:
    return list(_registry.keys())
