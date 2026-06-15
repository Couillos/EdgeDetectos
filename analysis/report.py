"""
15-panel chart report for edge analysis.
"""

import json
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
from pathlib import Path
from typing import Dict, List, Optional

from analysis.core import (
    DEFAULT_HORIZONS, HORIZON_LABELS, _to_native, _signal_returns,
    analyze_signal, compute_forward_returns
)

logging.getLogger('matplotlib').setLevel(logging.WARNING)
plt.rcParams['figure.max_open_warning'] = 0

# Theme
BG = '#0D1117'
PANEL = '#161B22'
TEXT = '#C9D1D9'
ACCENT = '#58A6FF'
GREEN = '#3FB950'
RED = '#F85149'
YELLOW = '#D29922'
PURPLE = '#BC8CFF'
GRID = '#21262D'
SIGNAL_COLOR = '#00D4AA'
ALL_COLOR = '#FF6B6B'


def style_ax(ax, title='', xlabel='', ylabel=''):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=11, fontweight='bold', pad=8)
    ax.set_xlabel(xlabel, color=TEXT, fontsize=9)
    ax.set_ylabel(ylabel, color=TEXT, fontsize=9)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.spines['bottom'].set_color(GRID)
    ax.spines['left'].set_color(GRID)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.15, color=GRID)


# ─── Panel Builders ──────────────────────────────────────────────────

def _build_panel_1(ax, horizon_stats, horizons):
    style_ax(ax, 'Horizon Mean Return %', 'Horizon', 'Mean Return %')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    means = [h.get('mean', 0) or 0 for h in hs]
    colors = [GREEN if m > 0 else RED for m in means]
    ax.bar(HORIZON_LABELS[:len(means)], means, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.5)
    for i, v in enumerate(means):
        ax.text(i, v + (0.01 if v >= 0 else -0.03), f'{v:.2f}%', ha='center', fontsize=7, color=TEXT)


def _build_panel_2(ax, horizon_stats, horizons):
    style_ax(ax, 'Win Rate %', 'Horizon', 'Win Rate %')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    wr = [h.get('winrate', 50) or 50 for h in hs]
    colors = [GREEN if w > 50 else RED for w in wr]
    ax.bar(HORIZON_LABELS[:len(wr)], wr, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
    ax.axhline(50, color=TEXT, linewidth=0.5, alpha=0.5, linestyle='--')
    for i, v in enumerate(wr):
        ax.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=7, color=TEXT)


def _build_panel_3(ax, horizon_stats, horizons):
    style_ax(ax, 'Sharpe Ratio', 'Horizon', 'Sharpe')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    sh = [h.get('sharpe', 0) or 0 for h in hs]
    colors = [GREEN if s > 0 else RED for s in sh]
    ax.bar(HORIZON_LABELS[:len(sh)], sh, color=colors, width=0.6, edgecolor='white', linewidth=0.5)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.5)
    for i, v in enumerate(sh):
        ax.text(i, v + (0.01 if v >= 0 else -0.03), f'{v:.2f}', ha='center', fontsize=7, color=TEXT)


def _build_panel_4(ax, signal_rets, all_rets, horizon_label='24h'):
    style_ax(ax, f'Return Distribution ({horizon_label})', 'Return %', 'Density')
    if len(signal_rets) > 2:
        ax.hist(signal_rets, bins=50, alpha=0.7, color=SIGNAL_COLOR, density=True, label='Signal')
    if len(all_rets) > 2:
        ax.hist(all_rets, bins=50, alpha=0.3, color=ALL_COLOR, density=True, label='All')
    ax.axvline(0, color=TEXT, linewidth=0.5, alpha=0.5)
    ax.legend(fontsize=7, labelcolor=TEXT)


def _build_panel_5(ax, signal_rets, all_rets, horizon_label='24h'):
    style_ax(ax, f'Q-Q Plot ({horizon_label})', 'Theoretical Quantiles', 'Sample Quantiles')
    if len(signal_rets) > 10:
        from scipy import stats
        stats.probplot(signal_rets, dist='norm', plot=ax)
        ax.get_lines()[0].set_color(SIGNAL_COLOR)
        if len(ax.get_lines()) > 1:
            ax.get_lines()[1].set_color(ACCENT)


def _build_panel_6(ax, horizon_stats, horizons):
    style_ax(ax, 'Signal Count', 'Horizon', 'N Signals')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    counts = [h.get('n_signals', 0) for h in hs]
    ax.bar(HORIZON_LABELS[:len(counts)], counts, color=ACCENT, width=0.6, edgecolor='white', linewidth=0.5)
    for i, v in enumerate(counts):
        ax.text(i, v + max(counts) * 0.01, f'{v}', ha='center', fontsize=7, color=TEXT)


def _build_panel_7(ax, rolling, horizon_label='24h'):
    style_ax(ax, f'Rolling Mean ({horizon_label})', 'Date', 'Mean %')
    if rolling.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    ax.plot(rolling['date'], rolling['mean'], color=SIGNAL_COLOR, linewidth=1)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.5, linestyle='--')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)


def _build_panel_8(ax, rolling):
    style_ax(ax, 'Rolling Sharpe', 'Date', 'Sharpe')
    if rolling.empty or 'sharpe' not in rolling.columns:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    ax.plot(rolling['date'], rolling['sharpe'], color=YELLOW, linewidth=1)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.5, linestyle='--')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)


def _build_panel_9(ax, yearly):
    style_ax(ax, 'Yearly Return %', 'Year', 'Return %')
    if yearly.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    means = yearly.set_index('year')['mean']
    colors = [GREEN if m > 0 else RED for m in means]
    ax.bar(means.index.astype(str), means.values, color=colors, width=0.6)
    for year, v in means.items():
        ax.text(year, v + (0.02 if v > 0 else -0.04), f'{v:.2f}%', ha='center', fontsize=8, color=TEXT)


def _build_panel_10_11(ax, equity_curves: Dict[int, pd.Series], horizons):
    style_ax(ax, 'Equity Curves', 'Date', 'Cumul. Return %')
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(horizons)))
    for h, color in zip(horizons, colors):
        if h in equity_curves and len(equity_curves[h]) > 0:
            ec = equity_curves[h]
            ax.plot(ec.index, ec.values, label=f'+{h}h', color=color, linewidth=0.8, alpha=0.85)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.3, linestyle='--')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)
    ax.legend(fontsize=6, labelcolor=TEXT, loc='upper left')


def _build_panel_12(ax, vol_regime):
    style_ax(ax, 'Performance by Vol Regime (24h)', 'Regime', 'Mean % / Excess')
    if vol_regime.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    x = range(len(vol_regime))
    ax.bar(x, vol_regime['mean'], width=0.35, color=SIGNAL_COLOR, label='Mean', alpha=0.8)
    ax.bar([i + 0.35 for i in x], vol_regime['excess_vs_random'], width=0.35,
           color=PURPLE, label='Excess', alpha=0.8)
    ax.set_xticks([i + 0.175 for i in x])
    ax.set_xticklabels(vol_regime['regime'], fontsize=8, color=TEXT)
    ax.axhline(0, color=TEXT, linewidth=0.5, alpha=0.5)
    ax.legend(fontsize=7, labelcolor=TEXT)


def _build_panel_13(ax, horizon_stats, horizons):
    style_ax(ax, 'P-Values (T-test)', 'Horizon', '-log10(p)')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    neg_log_p = [-np.log10(max(h.get('t_p', 1), 1e-10)) for h in hs]
    colors = [GREEN if p > -np.log10(0.05) else RED for p in neg_log_p]
    ax.bar(HORIZON_LABELS[:len(neg_log_p)], neg_log_p, color=colors, width=0.6)
    ax.axhline(-np.log10(0.05), color=YELLOW, linewidth=0.8, linestyle='--', label='p=0.05')
    ax.legend(fontsize=7, labelcolor=TEXT)
    for i, v in enumerate(neg_log_p):
        ax.text(i, v + 0.02, f'{v:.1f}', ha='center', fontsize=7, color=TEXT)


def _build_panel_14(ax, horizon_stats, horizons):
    style_ax(ax, 'MC- & KS-Test p-values', 'Horizon', '-log10(p)')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    neg_mc = [-np.log10(max(h.get('mc_p', 1), 1e-10)) for h in hs]
    neg_ks = [-np.log10(max(h.get('ks_p', 1), 1e-10)) for h in hs]
    x = range(len(hs))
    w = 0.35
    ax.bar([i - w / 2 for i in x], neg_mc, width=w, color=SIGNAL_COLOR, alpha=0.8, label='MC')
    ax.bar([i + w / 2 for i in x], neg_ks, width=w, color=ACCENT, alpha=0.8, label='KS')
    ax.set_xticks(list(x))
    ax.set_xticklabels(HORIZON_LABELS[:len(hs)], fontsize=8, color=TEXT)
    ax.axhline(-np.log10(0.05), color=YELLOW, linewidth=0.8, linestyle='--', label='p=0.05')
    ax.legend(fontsize=7, labelcolor=TEXT)


def _build_panel_15(ax, signal_rets, all_rets, horizon_label='1h'):
    style_ax(ax, f'Signal vs Random ({horizon_label})', 'Return %', 'Density')
    if len(signal_rets) > 2:
        ax.hist(signal_rets, bins=40, alpha=0.6, color=SIGNAL_COLOR, density=True, label='Signal')
    if len(all_rets) > 2:
        ax.hist(all_rets, bins=40, alpha=0.3, color=ALL_COLOR, density=True, label='Random')
    ax.axvline(0, color=TEXT, linewidth=0.5, alpha=0.5)
    ax.legend(fontsize=7, labelcolor=TEXT)


def _build_panel_16(ax, analysis, horizons, signal_name):
    style_ax(ax, 'Statistical Significance Matrix', '', 'Horizon')
    hs = [analysis['horizon_stats'].get(h, {}) for h in horizons]
    tests_data = []
    for h_stats in hs:
        neg_t = -np.log10(max(h_stats.get('t_p', 1), 1e-10))
        neg_ks = -np.log10(max(h_stats.get('ks_p', 1), 1e-10))
        neg_mc = -np.log10(max(h_stats.get('mc_p', 1), 1e-10))
        tests_data.append([neg_t, neg_ks, neg_mc])
    if not tests_data:
        ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    im = ax.imshow(np.array(tests_data).T, aspect='auto', cmap='RdYlGn',
                   vmin=0, vmax=2, interpolation='nearest')
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['T-test', 'KS-test', 'MC-test'], fontsize=8, color=TEXT)
    ax.set_xticks(range(len(horizons)))
    ax.set_xticklabels(HORIZON_LABELS[:len(horizons)], fontsize=8, color=TEXT)
    plt.colorbar(im, ax=ax, label='-log10(p)', shrink=0.8)
    for i in range(3):
        for j in range(len(horizons)):
            v = np.array(tests_data).T[i, j]
            ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=7,
                    color='white' if v > 1 else TEXT)


# ─── Full Report Generator ───────────────────────────────────────────

def generate_report(analysis: Dict, signal_name: str, output_path: str,
                    horizons: Optional[List[int]] = None):
    if horizons is None:
        horizons = DEFAULT_HORIZONS

    fig = plt.figure(figsize=(22, 30), facecolor=BG)
    gs = gridspec.GridSpec(16, 2, hspace=0.4, wspace=0.3,
                           left=0.05, right=0.95, top=0.97, bottom=0.02)

    horizon_stats = analysis['horizon_stats']
    rolling = analysis['rolling']
    yearly = analysis['yearly']
    vol_regime = analysis['vol_regime']
    equity_curves = analysis['equity_curves']
    signal_rets_by_h = analysis['signal_rets_by_h']
    all_rets_by_h = analysis['all_rets_by_h']

    fig.suptitle(f'Edge Analysis: {signal_name}', color=TEXT, fontsize=16, fontweight='bold', y=0.98)

    ax0 = fig.add_subplot(gs[0, :])
    ax0.set_facecolor(PANEL)
    ax0.axis('off')
    best_h = analysis.get('best_horizon')
    best_s = horizon_stats.get(best_h, {}) if best_h else {}
    info_lines = [
        f'Best Horizon: +{best_h}h' if best_h else 'Best Horizon: N/A',
        f'Trades: {best_s.get("n_signals", 0)}  |  Mean: {best_s.get("mean", 0):+.4f}%  |  Sharpe: {best_s.get("sharpe", 0):.4f}',
        f'Win Rate: {best_s.get("winrate", 0):.1f}%  |  T-test p: {best_s.get("t_p", 1):.4f}  |  MC p: {best_s.get("mc_p", 1):.4f}',
        f'Signal %: {analysis.get("signal_pct", 0):.1f}%  |  Signal Count: {analysis.get("signal_count", 0)}',
    ]
    for i, line in enumerate(info_lines):
        ax0.text(0.02, 0.75 - i * 0.18, line, transform=ax0.transAxes,
                fontsize=10, color=TEXT, fontfamily='monospace')

    panels = {
        1: ('Horizon Mean Return', _build_panel_1, [horizon_stats, horizons]),
        2: ('Win Rate', _build_panel_2, [horizon_stats, horizons]),
        3: ('Sharpe Ratio', _build_panel_3, [horizon_stats, horizons]),
        4: ('Return Distribution (24h)', _build_panel_4,
            [signal_rets_by_h.get(24, pd.Series()), all_rets_by_h.get(24, pd.Series()), '24h']),
        5: ('Q-Q Plot (24h)', _build_panel_5,
            [signal_rets_by_h.get(24, pd.Series()), all_rets_by_h.get(24, pd.Series()), '24h']),
        6: ('Signal Count', _build_panel_6, [horizon_stats, horizons]),
        7: ('Rolling Mean (24h)', _build_panel_7, [rolling, '24h']),
        8: ('Rolling Sharpe', _build_panel_8, [rolling]),
        9: ('Yearly Return', _build_panel_9, [yearly]),
        10: ('Equity Curves', _build_panel_10_11, [equity_curves, horizons]),
        11: (None, None, None),
        12: ('Vol Regime Analysis', _build_panel_12, [vol_regime]),
        13: ('T-test P-Values', _build_panel_13, [horizon_stats, horizons]),
        14: ('MC/KS P-Values', _build_panel_14, [horizon_stats, horizons]),
        15: ('Signal vs Random (1h)', _build_panel_15,
             [signal_rets_by_h.get(1, pd.Series()), all_rets_by_h.get(1, pd.Series()), '1h']),
        16: ('Significance Matrix', _build_panel_16, [analysis, horizons, signal_name]),
    }

    for pnl_num, (title, builder_fn, args) in panels.items():
        if builder_fn is None:
            continue
        if pnl_num <= 8:
            ax = fig.add_subplot(gs[pnl_num - 1, 0])
        elif pnl_num <= 15:
            ax = fig.add_subplot(gs[pnl_num - 1, 0])
        else:
            ax = fig.add_subplot(gs[pnl_num - 1, :])
        builder_fn(ax, *args)

    fig.savefig(output_path, dpi=120, facecolor=BG, bbox_inches='tight')
    plt.close(fig)


# ─── JSON Builder ────────────────────────────────────────────────────

def _build_analysis_json(analysis: Dict, signal_name: str,
                          source_file: str, report_image: str) -> Dict:
    hs = analysis['horizon_stats']
    rolling = analysis['rolling']
    yearly = analysis['yearly']
    vol_regime = analysis.get('vol_regime', pd.DataFrame())
    best_h = analysis.get('best_horizon')
    best_s = hs.get(best_h, {}) if best_h else hs.get(24, {})

    tests_count = 0
    best_t_p = 1.0
    best_mc_p = 1.0
    for h, s in hs.items():
        t_p = s.get('t_p', np.nan)
        ks_p = s.get('ks_p', np.nan)
        mc_p = s.get('mc_p', np.nan)
        if not np.isnan(t_p) and t_p < 0.05: tests_count += 1
        if not np.isnan(ks_p) and ks_p < 0.05: tests_count += 1
        if not np.isnan(mc_p) and mc_p < 0.05: tests_count += 1
        if not np.isnan(t_p): best_t_p = min(best_t_p, t_p)
        if not np.isnan(mc_p): best_mc_p = min(best_mc_p, mc_p)

    rolling_pos = float((rolling['mean'] > 0).mean() * 100) if not rolling.empty else 0.0

    verdict_map = {21: 'STRONG', 18: 'STRONG', 15: 'STRONG',
                   12: 'MODERATE', 9: 'MODERATE', 6: 'WEAK', 3: 'WEAK', 0: 'NONE'}
    for threshold, v in sorted(verdict_map.items(), reverse=True):
        if tests_count >= threshold:
            verdict = v
            break
    else:
        verdict = 'NONE'

    data = {
        'signal_name': signal_name,
        'source_file': source_file,
        'report_image': report_image,
        'verdict': verdict,
        'tests_significant': tests_count,
        'total_signals': int(best_s.get('n_signals', 0)),
        'signal_pct': _to_native(analysis['signal_pct']),
        'best_horizon': f'+{best_h}h' if best_h else '24h',
        'best_horizon_num': best_h,
        'best_sharpe': _to_native(best_s.get('sharpe')),
        'best_mean': _to_native(best_s.get('mean')),
        'best_winrate': _to_native(best_s.get('winrate')),
        'best_mc_p': _to_native(best_s.get('mc_p')),
        'best_t_p': _to_native(best_s.get('t_p')),
        'tests': {
            'best_t_test_p': _to_native(best_t_p),
            'best_mc_p': _to_native(best_mc_p),
            'tests_significant': tests_count,
        },
        'horizons': {},
        'persistence': {
            'rolling_windows_positive_pct': rolling_pos,
            'years_positive': int((yearly['mean'] > 0).sum()) if not yearly.empty else 0,
            'years_total': len(yearly),
            'years_significant': int((yearly['p_value'] < 0.05).sum()) if not yearly.empty else 0,
        },
    }

    for h, s in sorted(hs.items()):
        horizon_entry = {
            'n_signals': int(s.get('n_signals', 0)),
            'mean': _to_native(s.get('mean')),
            'std': _to_native(s.get('std')),
            'winrate': _to_native(s.get('winrate')),
            'sharpe': _to_native(s.get('sharpe')),
            't_p': _to_native(s.get('t_p')),
            'ks_p': _to_native(s.get('ks_p')),
            'mc_p': _to_native(s.get('mc_p')),
            'ci_low': _to_native(s.get('ci_low')),
            'ci_high': _to_native(s.get('ci_high')),
            'total_return': _to_native(s.get('total_return')),
        }
        data['horizons'][str(h)] = horizon_entry

    return data


# ─── analyze_edge (high-level entry point) ───────────────────────────

def analyze_edge(df: pd.DataFrame, signal_col: str = 'signal',
                 signal_name: str = 'Edge',
                 output_path: str = 'edge_analysis_report.png',
                 horizons: Optional[List[int]] = None,
                 source_file: str = '',
                 quick: bool = False):
    if horizons is None:
        horizons = DEFAULT_HORIZONS
    df = df.copy()
    if signal_col not in df.columns:
        has_fwd = any(c.startswith('fwd_') for c in df.columns)
        if not has_fwd:
            df = compute_forward_returns(df, horizons)
        if signal_col not in df.columns:
            raise ValueError(f"Column '{signal_col}' not found in DataFrame. "
                             "Compute it before calling analyze_edge.")

    print(f'[analyze] Running full analysis for "{signal_name}"...')
    analysis = analyze_signal(df, signal_col, horizons)
    if not quick:
        generate_report(analysis, signal_name, output_path, horizons)

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'analysis.json'
    json_data = _build_analysis_json(analysis, signal_name, source_file, str(output_path))
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f'[analyze] Saved JSON to {json_path}')

    h24 = analysis['horizon_stats'].get(24, {})
    print(f'[analyze] 24h mean: {h24.get("mean", np.nan):+.4f}% | '
          f'WR: {h24.get("winrate", np.nan):.1f}% | '
          f'T-p: {h24.get("t_p", np.nan):.4f} | '
          f'MC-p: {h24.get("mc_p", np.nan):.4f}')
    return analysis
