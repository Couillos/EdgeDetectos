"""
Backward-compatible shim: re-exports from engine package.
New code should import from 'engine' directly.
"""
from engine import eval_formula, list_indicators, generate_edge_file, INDICATORS
