"""
Backward-compatible shim: re-exports from analysis package.
New code should import from 'analysis' directly.
"""
from analysis import (
    analyze_signal, analyze_edge, generate_ranking,
    compute_forward_returns, generate_report, _build_analysis_json,
    DEFAULT_HORIZONS, HORIZON_LABELS, REPORTS_DIR
)
