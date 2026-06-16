"""
OOS worker: validates a single edge on OOS data.
"""

import json, os, sys, re
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

SPLIT_DATE = '2025-01-31'
MIN_SIGNALS_OOS = 5
MIN_SIGNALS_IS = 20
DEFAULT_HORIZONS = [1, 4, 6, 12, 24, 48, 72, 168]


def _oos_worker(args: tuple) -> Dict:
    edge_name, oos_parquet, bt_path, sm_path, reports_dir, split_date, horizons, quick = args

    sys.path.insert(0, os.path.dirname(bt_path))
    import pandas as pd
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    from edge_registry import register_edge, get_edge, _registry, Edge, ConditionFn
    from analysis.core import analyze_signal, compute_forward_returns
    from pathlib import Path

    result = {
        'edge_name': edge_name, 'verdict': 'FAIL', 'verdict_detail': '',
        'is_score': 0, 'oos_score': 0, 'final_score': 0,
        'decay': {}, 'is_vs_oos': {}, 'is': {}, 'oos': {},
    }

    df_oos = pd.read_parquet(oos_parquet)
    if len(df_oos) < 100:
        result['verdict_detail'] = f'OOS data too short ({len(df_oos)} rows)'
        return result

    # Register example edges
    def momentum_sma20_long(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        return (d['close'] > sma20).astype(int)
    register_edge(Edge(name="Price vs SMA20", entry_condition=momentum_sma20_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when close > SMA20"))
    def momentum_sma20_short(d):
        sma20 = d['close'].rolling(20).mean().bfill()
        return (-(d['close'] < sma20)).astype(int)
    register_edge(Edge(name="Price vs SMA20 Short", entry_condition=momentum_sma20_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when close < SMA20"))
    def rsi_oversold_long(d, period=14):
        delta = d['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean()
        avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l
        rsi = 100 - (100 / (1 + rs))
        return (rsi < 30).astype(int)
    register_edge(Edge(name="RSI 14 Oversold", entry_condition=rsi_oversold_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when RSI < 30"))
    def rsi_overbought_short(d, period=14):
        delta = d['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_g = gain.rolling(period).mean()
        avg_l = loss.rolling(period).mean()
        rs = avg_g / avg_l
        rsi = 100 - (100 / (1 + rs))
        return (-(rsi > 70)).astype(int)
    register_edge(Edge(name="RSI 14 Overbought Short", entry_condition=rsi_overbought_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when RSI > 70"))
    def bb_long(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean()
        sd = d['close'].rolling(period).std()
        lower = sma - std * sd
        return (d['close'] < lower).astype(int)
    register_edge(Edge(name="Bollinger Bands (20,2)", entry_condition=bb_long,
                       direction='long', close_horizons=[1, 6, 24],
                       description="Long when close < lower band"))
    def bb_short(d, period=20, std=2.0):
        sma = d['close'].rolling(period).mean()
        sd = d['close'].rolling(period).std()
        upper = sma + std * sd
        return (-(d['close'] > upper)).astype(int)
    register_edge(Edge(name="Bollinger Bands Short (20,2)", entry_condition=bb_short,
                       direction='short', close_horizons=[1, 6, 24],
                       description="Short when close > upper band"))

    # Load user edges
    edges_dir = Path(bt_path).parent / "edges"
    if edges_dir.exists():
        for pyfile in sorted(edges_dir.glob("*.py")):
            if pyfile.name == '__init__.py':
                continue
            try:
                ns = {'pd': pd, 'register_edge': register_edge,
                      'Edge': Edge, 'ConditionFn': ConditionFn,
                      '__builtins__': __builtins__}
                with open(pyfile, encoding='utf-8') as f:
                    code = compile(f.read(), pyfile.name, 'exec')
                    exec(code, ns)
                if 'register' in ns:
                    ns['register']()
            except Exception:
                pass

    edge = _registry.get(edge_name)
    if edge is None:
        result['verdict_detail'] = f'Edge "{edge_name}" not found in registry'
        return result

    # Load IS analysis
    safe_name = re.sub(r'[^\w\s-]', '', edge.name).strip().replace(' ', '_').lower()
    is_json_path = Path(reports_dir) / safe_name / 'analysis.json'
    if not is_json_path.exists():
        result['verdict_detail'] = 'No IS analysis found'
        return result
    with open(is_json_path) as f:
        is_data = json.load(f)

    # Run signal on OOS
    df_oos = compute_forward_returns(df_oos, horizons)
    df_oos = df_oos.copy()
    try:
        signals = edge.entry_condition(df_oos)
        df_oos['signal'] = signals
    except Exception as e:
        result['verdict_detail'] = f'Signal computation failed: {e}'
        return result

    try:
        oos_analysis = analyze_signal(df_oos, 'signal', horizons)
    except Exception as e:
        result['verdict_detail'] = f'Analysis failed: {e}'
        return result
    oos_best_h = oos_analysis.get('best_horizon')
    oos_best_s = {}
    if oos_best_h and oos_best_h in oos_analysis.get('horizon_stats', {}):
        oos_best_s = oos_analysis['horizon_stats'][oos_best_h]

    is_best_h = is_data.get('best_horizon_num')
    is_best_s = {}
    if is_best_h:
        is_best_s = is_data.get('horizons', {}).get(str(is_best_h), {})

    is_score = _compute_is_score(is_data, is_best_s)
    oos_score = _compute_oos_score(oos_analysis, oos_best_s, is_best_s)
    decay = _compute_decay(is_data, oos_analysis, is_best_s, oos_best_s)
    is_vs_oos = _is_vs_oos_tests(is_data, oos_analysis, is_best_s)
    final_score = _compute_final_score(is_score, oos_score, decay)
    verdict = _classify_edge(is_score, oos_score, decay, is_best_s, oos_best_s)

    result.update({
        'verdict': verdict['label'], 'verdict_detail': verdict['detail'],
        'is_score': round(is_score, 2), 'oos_score': round(oos_score, 2),
        'final_score': round(final_score, 2), 'decay': decay,
        'is_vs_oos': is_vs_oos,
        'is': {'best_horizon': is_best_h, 'best_stats': is_best_s,
               'signal_count': is_data.get('total_signals', 0),
               'signal_pct': is_data.get('signal_pct', 0)},
        'oos': {'best_horizon': oos_best_h, 'best_stats': oos_best_s,
                'signal_count': oos_analysis.get('signal_count', 0),
                'signal_pct': oos_analysis.get('signal_pct', 0),
                'horizon_stats': oos_analysis.get('horizon_stats', {})},
    })
    return result


def _compute_is_score(is_data: Dict, best_s: Dict) -> float:
    if not best_s or best_s.get('n_signals', 0) < MIN_SIGNALS_IS:
        return 0.0
    n = best_s.get('n_signals', 0)
    sharpe = best_s.get('sharpe', 0) or 0
    winrate = best_s.get('winrate', 50) or 50
    t_p = best_s.get('t_p', 1) or 1
    mc_p = best_s.get('mc_p', 1) or 1
    ks_p = best_s.get('ks_p', 1) or 1

    sig_score = 0.0
    for p in [t_p, mc_p, ks_p]:
        if p < 0.05:
            sig_score += min(-np.log10(max(p, 1e-10)) / 1.3 * 13.33, 13.33)

    sharpe_score = min(max(sharpe, 0) * 12.5, 25.0)
    wr_score = min(max(winrate - 50, 0) * 1.5, 15.0)

    horizons = is_data.get('horizons', {})
    sig_horizons = sum(
        1 for h_stats in horizons.values()
        if h_stats.get('t_p', 1) < 0.05 and h_stats.get('mc_p', 1) < 0.05
    )
    breadth_score = min(sig_horizons / max(len(horizons), 1) * 20, 20.0)

    total = sig_score + sharpe_score + wr_score + breadth_score
    count_factor = min(n / 200, 1.0) * 0.2 + 0.8
    return total * count_factor


def _compute_oos_score(oos_analysis: Dict, oos_best_s: Dict, is_best_s: Dict) -> float:
    if not oos_best_s or oos_best_s.get('n_signals', 0) < MIN_SIGNALS_OOS:
        return 0.0
    n = oos_best_s.get('n_signals', 0)
    is_n = is_best_s.get('n_signals', 1)
    sharpe = oos_best_s.get('sharpe', 0) or 0
    winrate = oos_best_s.get('winrate', 50) or 50
    t_p = oos_best_s.get('t_p', 1) or 1
    mc_p = oos_best_s.get('mc_p', 1) or 1
    ks_p = oos_best_s.get('ks_p', 1) or 1

    expected_ratio = 17 / 60
    actual_ratio = n / max(is_n, 1)
    signal_adequacy = min(actual_ratio / expected_ratio, 1.0)

    sig_score = 0.0
    for p in [t_p, mc_p, ks_p]:
        if p < 0.05:
            sig_score += min(-np.log10(max(p, 1e-10)) / 1.3 * 13.33, 13.33)
    sig_score *= signal_adequacy

    sharpe_score = min(max(sharpe, 0) * 12.5, 25.0) * signal_adequacy
    wr_score = min(max(winrate - 50, 0) * 1.5, 15.0) * signal_adequacy

    horizons = oos_analysis.get('horizon_stats', {})
    sig_horizons = sum(
        1 for h_stats in horizons.values()
        if h_stats.get('n_signals', 0) >= 10
        and h_stats.get('t_p', 1) < 0.05
        and h_stats.get('mc_p', 1) < 0.05
    )
    breadth_score = min(sig_horizons / max(len(horizons), 1) * 20, 20.0)

    return sig_score + sharpe_score + wr_score + breadth_score


def _compute_decay(is_data: Dict, oos_analysis: Dict,
                   is_best_s: Dict, oos_best_s: Dict) -> Dict:
    if not is_best_s or is_best_s.get('n_signals', 0) < MIN_SIGNALS_IS:
        return {'composite_decay': 1.0, 'sharpe_decay': 1.0,
                'mean_decay': 1.0, 'winrate_decay': 1.0,
                'dist_ks_p': None, 'dist_decay': 0.5, 'signal_freq_decay': 0.0}

    if not oos_best_s or oos_best_s.get('n_signals', 0) < MIN_SIGNALS_OOS:
        return {'composite_decay': 1.0, 'sharpe_decay': 1.0,
                'mean_decay': 1.0, 'winrate_decay': 1.0,
                'dist_ks_p': None, 'dist_decay': 1.0, 'signal_freq_decay': 1.0}

    is_sharpe = is_best_s.get('sharpe', 0) or 0
    oos_sharpe = oos_best_s.get('sharpe', 0) or 0
    is_mean = is_best_s.get('mean', 0) or 0
    oos_mean = oos_best_s.get('mean', 0) or 0
    is_wr = is_best_s.get('winrate', 50) or 50
    oos_wr = oos_best_s.get('winrate', 50) or 50
    is_n = is_best_s.get('n_signals', 1)
    oos_n = oos_best_s.get('n_signals', 0)

    if is_sharpe > 0.02:
        sharpe_decay = max(0, min((is_sharpe - max(oos_sharpe, 0)) / is_sharpe, 1.0))
    elif is_sharpe < -0.02 and oos_sharpe > 0.02:
        sharpe_decay = 1.0
    else:
        sharpe_decay = 0.5

    if abs(is_mean) > 0.01:
        if oos_mean < 0 and is_mean > 0:
            mean_decay = min(1.0, abs(is_mean - oos_mean) / abs(is_mean))
        else:
            mean_decay = max(0, (is_mean - oos_mean) / is_mean) if is_mean > 0 else 0
        mean_decay = min(mean_decay, 1.0)
    else:
        mean_decay = 0.5

    is_edge = is_wr - 50
    oos_edge = oos_wr - 50
    if is_edge > 2:
        winrate_decay = max(0, (is_edge - max(oos_edge, 0)) / is_edge)
        winrate_decay = min(winrate_decay, 1.0)
    else:
        winrate_decay = 0.3

    dist_ks_p = None
    dist_decay = 0.5
    is_best_h = is_data.get('best_horizon_num')
    if is_best_h:
        oos_hs = oos_analysis.get('horizon_stats', {})
        if is_best_h in oos_hs:
            oos_mc_p = oos_hs[is_best_h].get('mc_p', 1) or 1
            dist_ks_p = oos_mc_p
            dist_decay = max(0, min(1 - dist_ks_p * 2, 1.0)) if dist_ks_p is not None else 0.5

    is_pct = is_data.get('signal_pct', 0) or 0
    oos_pct = oos_analysis.get('signal_pct', 0) or 0
    freq_decay = min(abs(is_pct - oos_pct) / max(is_pct, 0.01), 1.0) if is_pct > 0.01 else 0.0

    weights = {'sharpe_decay': 0.30, 'mean_decay': 0.20,
               'winrate_decay': 0.15, 'dist_decay': 0.25, 'freq_decay': 0.10}
    composite = (
        sharpe_decay * weights['sharpe_decay'] +
        mean_decay * weights['mean_decay'] +
        winrate_decay * weights['winrate_decay'] +
        dist_decay * weights['dist_decay'] +
        freq_decay * weights['freq_decay']
    )

    return {
        'sharpe_decay': round(sharpe_decay, 4), 'mean_decay': round(mean_decay, 4),
        'winrate_decay': round(winrate_decay, 4),
        'dist_ks_p': dist_ks_p, 'dist_decay': round(dist_decay, 4),
        'signal_freq_decay': round(freq_decay, 4), 'composite_decay': round(composite, 4),
    }


def _is_vs_oos_tests(is_data: Dict, oos_analysis: Dict, is_best_s: Dict) -> Dict:
    is_t_p = is_best_s.get('t_p', 1) or 1
    is_mc_p = is_best_s.get('mc_p', 1) or 1

    oos_best_h = oos_analysis.get('best_horizon')
    oos_s = oos_analysis.get('horizon_stats', {}).get(oos_best_h, {}) if oos_best_h else {}
    oos_t_p = oos_s.get('t_p', 1) or 1
    oos_mc_p = oos_s.get('mc_p', 1) or 1

    return {
        'is_t_p': is_t_p, 'is_mc_p': is_mc_p,
        'oos_t_p': oos_t_p, 'oos_mc_p': oos_mc_p,
        't_improved': oos_t_p < is_t_p,
        'mc_improved': oos_mc_p < is_mc_p,
    }


def _compute_final_score(is_score: float, oos_score: float, decay: Dict) -> float:
    composite_decay = decay.get('composite_decay', 1.0)
    if is_score <= 0 and oos_score <= 0:
        return 0.0
    weighted = is_score * 0.25 + oos_score * 0.75
    decay_multiplier = 1.0 - composite_decay * 0.7
    return max(weighted * decay_multiplier, 0.0)


def _classify_edge(is_score: float, oos_score: float, decay: Dict,
                   is_best_s: Dict, oos_best_s: Dict) -> Dict:
    composite_decay = decay.get('composite_decay', 1.0)
    oos_n = oos_best_s.get('n_signals', 0)
    oos_sharpe = oos_best_s.get('sharpe', 0) or 0
    oos_t_p = oos_best_s.get('t_p', 1) or 1
    oos_mc_p = oos_best_s.get('mc_p', 1) or 1
    is_sharpe = is_best_s.get('sharpe', 0) or 0

    if oos_n < MIN_SIGNALS_OOS:
        return {'label': 'FAIL', 'detail': f'Only {oos_n} OOS signals'}
    if oos_sharpe < -0.05 and (oos_t_p < 0.10 or oos_mc_p < 0.10):
        return {'label': 'FAIL', 'detail': f'Significantly negative OOS ({oos_sharpe:.3f})'}
    if is_sharpe > 0.3 and oos_sharpe < -0.3:
        return {'label': 'FAIL', 'detail': f'Edge flipped ({is_sharpe:.2f}→{oos_sharpe:.2f})'}
    if composite_decay > 0.85:
        return {'label': 'FAIL', 'detail': f'Decay {composite_decay:.2f} > 0.85'}

    composite_score = is_score * 0.25 + oos_score * 0.50 + (1 - composite_decay) * 100 * 0.25
    weak_reasons = []
    if is_score < 20:
        weak_reasons.append(f'Low IS ({is_score:.1f})')
    if oos_t_p > 0.15 and oos_mc_p > 0.15:
        weak_reasons.append(f'OOS not sig (t={oos_t_p:.3f})')
    if composite_decay > 0.60:
        weak_reasons.append(f'High decay ({composite_decay:.2f})')
    if oos_sharpe < 0.05:
        weak_reasons.append(f'Low OOS sharpe ({oos_sharpe:.3f})')

    if weak_reasons and composite_score < 45:
        return {'label': 'WEAK', 'detail': '; '.join(weak_reasons)}
    if composite_score >= 70 and not weak_reasons:
        return {'label': 'STRONG', 'detail': f'Score {composite_score:.1f}'}
    if composite_score >= 45:
        return {'label': 'PASS', 'detail': f'Score {composite_score:.1f}'}
    return {'label': 'WEAK', 'detail': f'Score {composite_score:.1f}'}
