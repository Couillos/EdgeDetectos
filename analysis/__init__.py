"""
Analysis package: signal stats, chart reports, and ranking.
"""

from analysis.core import (
    analyze_signal, compute_forward_returns, DEFAULT_HORIZONS,
    HORIZON_LABELS, REPORTS_DIR
)
from analysis.report import (
    analyze_edge, generate_report, _build_analysis_json
)
from analysis.ranking import generate_ranking
