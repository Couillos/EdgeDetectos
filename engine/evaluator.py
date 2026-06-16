"""
Evaluator: walks the AST and produces pandas Series.
Also includes eval_formula(), generate_edge_file(), list_indicators().
"""

import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.language import (
    Node, Number, Ident, Shift, UnaryOp, BinOp, FuncCall, parse, ParseError
)
from engine.indicators import INDICATORS, _get_index


# ─── Evaluator ───────────────────────────────────────────────────────

def _resolve_col(data: Dict[str, pd.Series], name: str) -> pd.Series:
    if name in data:
        return data[name]
    raise NameError(f"Unknown column or indicator: '{name}'. "
                    f"Available columns: {list(data.keys())}")


def evaluate(node: Node, data: Dict[str, pd.Series]) -> pd.Series:
    if isinstance(node, Number):
        idx = _get_index(data)
        if idx is not None:
            return pd.Series(float(node.value), index=idx)
        return pd.Series([float(node.value)])

    if isinstance(node, Ident):
        return _resolve_col(data, node.name)

    if isinstance(node, Shift):
        if node.expr is not None:
            val = evaluate(node.expr, data)
            return val.shift(node.n)
        col = _resolve_col(data, node.ident)
        return col.shift(node.n)

    if isinstance(node, UnaryOp):
        val = evaluate(node.expr, data)
        if node.op == '-':
            return -val
        raise ValueError(f'Unknown unary operator: {node.op}')

    if isinstance(node, BinOp):
        left = evaluate(node.left, data)
        right = evaluate(node.right, data)

        if node.op == '+': return left + right
        if node.op == '-': return left - right
        if node.op == '*': return left * right
        if node.op == '/': return left / right.replace(0, np.nan)
        if node.op == '<': return (left < right).astype(int)
        if node.op == '>': return (left > right).astype(int)
        if node.op == '<=': return (left <= right).astype(int)
        if node.op == '>=': return (left >= right).astype(int)
        if node.op == '==': return (left == right).astype(int)
        if node.op == '!=': return (left != right).astype(int)
        if node.op == '&': return (left.astype(bool) & right.astype(bool)).astype(int)
        if node.op == '|': return (left.astype(bool) | right.astype(bool)).astype(int)
        raise ValueError(f'Unknown operator: {node.op}')

    if isinstance(node, FuncCall):
        if node.name not in INDICATORS:
            raise NameError(f"Unknown indicator: '{node.name}'. "
                            f"Available: {list(INDICATORS.keys())}")
        info = INDICATORS[node.name]
        resolved_args = []
        for arg in node.args:
            if isinstance(arg, Ident):
                resolved_args.append(arg.name)
            elif isinstance(arg, (Number,)):
                resolved_args.append(arg.value)
            else:
                val = evaluate(arg, data)
                temp_name = f'__tmp_{id(arg)}'
                data[temp_name] = val
                resolved_args.append(temp_name)

        signal = info['fn'](data, *resolved_args)

        for arg in node.args:
            temp_name = f'__tmp_{id(arg)}'
            if temp_name in data:
                del data[temp_name]

        return signal

    raise TypeError(f'Unknown node type: {type(node)}')


# ─── eval_formula ────────────────────────────────────────────────────

def eval_formula(formula: str, df: pd.DataFrame) -> pd.Series:
    """Parse and evaluate a formula string against a DataFrame.
    Returns a Series with values 1 (LONG), -1 (SHORT), or 0 (NEUTRAL).
    """
    data = {col: df[col].copy() for col in df.columns}
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col not in data and col in df.columns:
            data[col] = df[col].copy()

    ast = parse(formula)
    result = evaluate(ast, data)
    result = result.fillna(0).astype(int)
    return result


# ─── Edge File Generator ─────────────────────────────────────────────

def generate_edge_file(name: str, long_formula: Optional[str] = None,
                       short_formula: Optional[str] = None,
                       horizons: Optional[List[int]] = None,
                       description: str = '',
                       output_dir: str = 'edges',
                       metric: str = 'ohlcv',
                       timeframe: str = '1h') -> str:
    if horizons is None:
        horizons = [1, 4, 6, 12, 24, 48, 72, 168]
    if not long_formula and not short_formula:
        raise ValueError('At least one of long_formula or short_formula is required')
    if long_formula and short_formula:
        raise ValueError('An edge must be either long OR short, not both. Use --long OR --short.')

    if long_formula:
        direction = 'long'
        formula_str = long_formula
    else:
        direction = 'short'
        formula_str = short_formula

    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_').replace('-', '_')
    if safe_name and safe_name[0].isdigit():
        safe_name = '_' + safe_name
    filename = safe_name.lower() + '.py'
    filepath = Path(output_dir) / filename

    if direction == 'long':
        return_line = f'    return eval_formula({repr(formula_str)}, df)'
    else:
        return_line = f'    return -eval_formula({repr(formula_str)}, df)'

    lines = [
        '"""',
        f'{name}',
        'Generated edge from formula engine.',
        f'{direction.title()}: {formula_str}',
        f'Metric: {metric}, Timeframe: {timeframe}',
        '"""',
        '',
        'import pandas as pd',
        'import numpy as np',
        'from formula_engine import eval_formula',
        '',
        '',
        f'def {safe_name}_condition(df: pd.DataFrame) -> pd.Series:',
        f'    """Return 1 for {direction} signal, 0 otherwise."""',
        return_line,
        '',
        '',
        'def register():',
        '    from backtest import register_edge, Edge',
        '    register_edge(Edge(',
        f'        name={repr(name)},',
        f'        entry_condition={safe_name}_condition,',
        f'        close_horizons={horizons},',
        f'        description={repr(description)},',
        f'        direction={repr(direction)},',
        f'        metric={repr(metric)},',
        f'        timeframe={repr(timeframe)},',
        '    ))',
        '',
    ]

    filepath.write_text('\n'.join(lines) + '\n')
    return str(filepath)


# ─── List Indicators ─────────────────────────────────────────────────

def list_indicators():
    lines = []
    lines.append('=' * 70)
    total = len(INDICATORS)
    lines.append(f'AVAILABLE INDICATORS ({total} total)')
    lines.append('=' * 70)

    categories = {}
    for name, info in sorted(INDICATORS.items()):
        cat = info['category']
        categories.setdefault(cat, []).append((name, info))

    for cat, items in categories.items():
        lines.append(f'\n  [{cat}]')
        for name, info in items:
            lines.append(f'    {name:20s} {info["description"]}')

    lines.append('')
    lines.append('=' * 70)
    lines.append('BUILT-IN REFERENCES (OHLCV): open, high, low, close, volume')
    lines.append('')
    lines.append('MARKET METRICS (use --metric to specify):')
    lines.append('  ohlcv              OHLCV (open, high, low, close, volume)')
    lines.append('  funding_rate       Binance Futures (funding_rate, mark_price)')
    lines.append('  open_interest      Bybit (open_interest, open_interest_usd)')
    lines.append('  taker_volume       Binance (taker_buy_*, taker_sell_*)')
    lines.append('  long_short_ratio   Bybit (buy_ratio, sell_ratio, ls_ratio)')
    lines.append('')
    lines.append('When --metric is specified, those columns are merged into the DataFrame')
    lines.append('and can be referenced directly in formulas (e.g. funding_rate > -0.01).')
    lines.append('')
    lines.append('OPERATORS: +, -, *, /, <, >, <=, >=, ==, !=, &, |')
    lines.append('SHIFT: close.shift(6)')
    lines.append('')
    lines.append('EXAMPLES:')
    lines.append('  close < sma(close, 20) * 0.98')
    lines.append('  rsi(close, 14) < 30 & close < bb_lower(close, 20, 2)')
    lines.append('  consecutive_red(3)')
    lines.append('  close > ema(close, 50) & macd_hist(close) > 0')
    lines.append('  close < donchian_lower(close, 20)')
    lines.append('  funding_rate < -0.01 & close > sma(close, 20)')
    lines.append('  open_interest > open_interest.shift(24) & close > ema(close, 50)')
    lines.append('=' * 70)

    return '\n'.join(lines)
