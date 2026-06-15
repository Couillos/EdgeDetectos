"""
Backward-compatible entry point.
Imports from refactored modules. Edge files import from here.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from edge_registry import Edge, register_edge, get_edge, list_edges, _registry, ConditionFn
from bt_engine.data import load_data, register_example_edges, load_user_edges
from bt_engine.engine import BacktestEngine, generate_legacy_report, generate_edge_report
from bt_engine.worker import _mp_run_edge
from analysis.ranking import generate_ranking
from analysis.report import analyze_edge
from engine.evaluator import generate_edge_file, list_indicators

from cli import main

if __name__ == '__main__':
    main()
