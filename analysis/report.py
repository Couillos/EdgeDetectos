"""
6x3 panel chart report matching original edge_testing_documentation.txt layout.
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
    DEFAULT_HORIZONS, HORIZON_LABELS, _to_native,
    analyze_signal, compute_forward_returns, monte_carlo_permutation
)

logging.getLogger('matplotlib').setLevel(logging.WARNING)
plt.rcParams['figure.max_open_warning'] = 0

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
LEGEND_KW = {'facecolor': '#0A0D14', 'edgecolor': '#C9D1D9', 'framealpha': 0.95}


def _legend(ax, *args, **kwargs):
    for k, v in LEGEND_KW.items():
        kwargs.setdefault(k, v)
    return ax.legend(*args, **kwargs)


def style_ax(ax, title='', xlabel='', ylabel=''):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.spines['left'].set_color(GRID)
    if title:
        ax.set_title(title, color=ACCENT, fontsize=11, fontweight='bold', pad=6)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT, fontsize=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT, fontsize=8)


def _build_panel_r1c1(ax, horizon_stats, horizons):
    """Mean Forward Return by Horizon with bootstrap 95% CI error bars."""
    style_ax(ax, 'Mean Forward Return by Horizon', 'Horizon', 'Mean Return %')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    means = [h.get('mean', 0) or 0 for h in hs]
    ci_low = [h.get('ci_low', 0) or 0 for h in hs]
    ci_high = [h.get('ci_high', 0) or 0 for h in hs]
    colors = [GREEN if m > 0 else RED for m in means]
    bars = ax.bar(range(len(means)), means, color=colors, alpha=0.8, width=0.6,
                  edgecolor='white', linewidth=0.5)
    yerr_low = [m - l for m, l in zip(means, ci_low)]
    yerr_high = [h - m for m, h in zip(means, ci_high)]
    ax.errorbar(range(len(means)), means,
                yerr=[yerr_low, yerr_high],
                fmt='none', color=TEXT, capsize=3, linewidth=1)
    ax.axhline(0, color=GRID, linewidth=0.5)
    ax.set_xticks(range(len(means)))
    ax.set_xticklabels(HORIZON_LABELS[:len(means)], fontsize=7, color=TEXT)
    for i, v in enumerate(means):
        ax.text(i, v + (0.02 if v >= 0 else -0.05), f'{v:+.3f}%',
                ha='center', fontsize=7, color=GREEN if v > 0 else RED,
                fontweight='bold')


def _build_panel_r1c2(ax, horizon_stats, horizons):
    """Winrate by Horizon."""
    style_ax(ax, 'Winrate by Horizon', 'Horizon', 'Win Rate %')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    wr = [h.get('winrate', 50) or 50 for h in hs]
    colors = [GREEN if w > 50 else RED for w in wr]
    ax.bar(range(len(wr)), wr, color=colors, alpha=0.8, width=0.6,
           edgecolor='white', linewidth=0.5)
    ax.axhline(50, color=YELLOW, linewidth=0.8, linestyle='--', label='50% baseline')
    _legend(ax, fontsize=7, labelcolor=TEXT)
    ax.set_xticks(range(len(wr)))
    ax.set_xticklabels(HORIZON_LABELS[:len(wr)], fontsize=7, color=TEXT)
    for i, v in enumerate(wr):
        ax.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=7, color=TEXT, fontweight='bold')


def _build_panel_r1c3(ax, horizon_stats, horizons):
    """Statistical Significance Matrix (heatmap)."""
    style_ax(ax, 'Statistical Significance Matrix', '', 'Test')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    neg_log = np.array([
        [-np.log10(max(h.get('t_p', 1), 1e-10)) for h in hs],
        [-np.log10(max(h.get('ks_p', 1), 1e-10)) for h in hs],
        [-np.log10(max(h.get('mc_p', 1), 1e-10)) for h in hs],
    ])
    vmin, vmax = 0, max(2, np.nanmax(neg_log))
    im = ax.imshow(neg_log, aspect='auto', cmap='RdYlGn',
                   vmin=vmin, vmax=vmax, interpolation='nearest')
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['T-test', 'KS-test', 'MC-test'], fontsize=7, color=TEXT)
    ax.set_xticks(range(len(horizons)))
    ax.set_xticklabels(HORIZON_LABELS[:len(horizons)], fontsize=7, color=TEXT)
    for i in range(3):
        for j in range(len(horizons)):
            v = neg_log[i, j]
            ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=7,
                    color='white' if v > vmax * 0.5 else TEXT)
    plt.colorbar(im, ax=ax, label='-log10(p)', shrink=0.8)


def _build_panel_r2c1(ax, signal_rets, all_rets, horizon_label='24h'):
    """Return Distribution Signal vs All (overlaid histogram)."""
    style_ax(ax, f'Return Distribution Signal vs All ({horizon_label})',
             'Return %', 'Density')
    bins = np.linspace(-15, 15, 80)
    if len(all_rets) > 2:
        ax.hist(all_rets, bins=bins, alpha=0.35, color=ALL_COLOR, density=True, label='All')
    if len(signal_rets) > 2:
        ax.hist(signal_rets, bins=bins, alpha=0.5, color=SIGNAL_COLOR, density=True, label='Signal')
    ax.axvline(0, color=YELLOW, linewidth=0.8, linestyle='--')
    signal_mean = float(signal_rets.mean()) if len(signal_rets) > 0 else 0
    ax.axvline(signal_mean, color=SIGNAL_COLOR, linewidth=1.5,
               label=f'Signal mean: {signal_mean:+.4f}%')
    _legend(ax, fontsize=7, labelcolor=TEXT, loc='upper right')


def _build_panel_r2c2(ax, signal_rets, all_rets, horizon_label='24h'):
    """Monte Carlo vs Signal (histogram of random means)."""
    style_ax(ax, f'Monte Carlo vs Signal ({horizon_label})', 'Mean Return %', 'Density')
    np.random.seed(42)
    n = len(signal_rets)
    if n < 2 or len(all_rets) < n:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes,
                ha='center', color=TEXT)
        return
    mc_means = []
    for _ in range(1000):
        sample = np.random.choice(all_rets, size=n, replace=False)
        mc_means.append(np.mean(sample))
    mc_means = np.array(mc_means)
    mc_p = (mc_means >= float(signal_rets.mean())).mean()
    mc_p_upper = (mc_means <= float(signal_rets.mean())).mean()
    mc_p_val = min(mc_p, mc_p_upper) * 2
    ax.hist(mc_means, bins=50, alpha=0.5, color=ALL_COLOR, density=True, label='Random means')
    ax.axvline(signal_rets.mean(), color=SIGNAL_COLOR, linewidth=2.5,
               label=f'Signal mean: {signal_rets.mean():+.4f}%')
    ax.axvline(mc_means.mean(), color=RED, linewidth=1.0, linestyle='--',
               label=f'Random mean: {mc_means.mean():+.4f}%')
    _legend(ax, fontsize=7, labelcolor=TEXT, loc='upper left')
    p_color = GREEN if mc_p_val < 0.05 else RED
    ax.text(0.95, 0.95, f'MC p={mc_p_val:.4f}', transform=ax.transAxes,
            ha='right', va='top', fontsize=9, fontweight='bold',
            color=p_color,
            bbox=dict(boxstyle='round', facecolor=PANEL, edgecolor=p_color, alpha=0.8))


def _build_panel_r2c3(ax, horizon_stats, horizons):
    """Sharpe-like Ratio by Horizon."""
    style_ax(ax, 'Sharpe-like Ratio by Horizon', 'Horizon', 'Sharpe')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    sh = [h.get('sharpe', 0) or 0 for h in hs]
    colors = [GREEN if s > 0 else RED for s in sh]
    ax.bar(range(len(sh)), sh, color=colors, alpha=0.8, width=0.6,
           edgecolor='white', linewidth=0.5)
    ax.axhline(0, color=GRID, linewidth=0.5)
    ax.set_xticks(range(len(sh)))
    ax.set_xticklabels(HORIZON_LABELS[:len(sh)], fontsize=7, color=TEXT)
    for i, v in enumerate(sh):
        ax.text(i, v + (0.01 if v >= 0 else -0.03), f'{v:.4f}',
                ha='center', fontsize=7, color=GREEN if v > 0 else RED)


def _build_panel_r3c1(ax, rolling):
    """Rolling Edge Decay 24h Mean Return (time bar chart)."""
    style_ax(ax, 'Rolling Edge Decay (24h Mean Return)', 'Date', 'Mean %')
    if rolling.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    colors = [GREEN if v > 0 else RED for v in rolling['mean']]
    ax.bar(rolling['date'], rolling['mean'], width=25, color=colors, alpha=0.8)
    ax.axhline(0, color=YELLOW, linewidth=0.8, linestyle='--')
    overall_mean = rolling['mean'].mean()
    ax.axhline(overall_mean, color=ACCENT, linewidth=1.0, label=f'Overall avg: {overall_mean:.4f}%')
    if len(rolling) > 5:
        rolling['mean_ma'] = rolling['mean'].rolling(5, min_periods=1).mean()
        ax.plot(rolling['date'], rolling['mean_ma'], color=YELLOW, linewidth=1.0,
                label='5-period MA')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)
    _legend(ax, fontsize=7, labelcolor=TEXT)


def _build_panel_r3c2(ax, rolling):
    """Rolling Winrate 24h (time bar chart)."""
    style_ax(ax, 'Rolling Winrate (24h)', 'Date', 'Win Rate %')
    if rolling.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    colors = [GREEN if v > 50 else RED for v in rolling['winrate']]
    ax.bar(rolling['date'], rolling['winrate'], width=25, color=colors, alpha=0.8)
    ax.axhline(50, color=YELLOW, linewidth=0.8, linestyle='--')
    overall_wr = rolling['winrate'].mean()
    ax.axhline(overall_wr, color=ACCENT, linewidth=1.0, label=f'Overall WR: {overall_wr:.1f}%')
    if len(rolling) > 5:
        rolling['wr_ma'] = rolling['winrate'].rolling(5, min_periods=1).mean()
        ax.plot(rolling['date'], rolling['wr_ma'], color=YELLOW, linewidth=1.0,
                label='5-period MA')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)
    _legend(ax, fontsize=7, labelcolor=TEXT)


def _build_panel_r3c3(ax, yearly):
    """Year-by-Year Performance (bar + twin axis winrate)."""
    style_ax(ax, 'Year-by-Year Performance', 'Year', 'Mean Return %')
    if yearly.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    years = yearly.set_index('year')
    colors = [GREEN if m > 0 else RED for m in years['mean']]
    bars = ax.bar(years.index.astype(str), years['mean'], color=colors, alpha=0.8, width=0.6)
    ax.axhline(0, color=GRID, linewidth=0.5)
    for idx, (year, row) in enumerate(years.iterrows()):
        label = f'{row["mean"]:.2f}%\nn={int(row["n"])}'
        if row['p_value'] < 0.05:
            label += ' ***'
        elif row['p_value'] < 0.1:
            label += ' **'
        ax.text(idx, row['mean'] + (0.02 if row['mean'] >= 0 else -0.05),
                label, ha='center', fontsize=6, color=TEXT)
    ax2 = ax.twinx()
    ax2.set_ylabel('Win Rate %', color=ACCENT, fontsize=8)
    ax2.plot(years.index.astype(str), years['winrate'], color=ACCENT,
             marker='o', linewidth=1.5, markersize=4)
    ax2.axhline(50, color=YELLOW, linewidth=0.5, linestyle='--')
    ax2.tick_params(colors=ACCENT, labelsize=7)
    ax2.spines['right'].set_color(ACCENT)
    ax2.spines['top'].set_visible(False)


def _build_panel_r4c12(ax, equity_curves, horizons):
    """Cumulative PnL (step plot with fill) - ALL horizons."""
    style_ax(ax, 'Cumulative PnL - All Horizons', 'Date', 'Cumul. Return %')
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(horizons)))
    has_data = False
    for h, color in zip(horizons, colors):
        if h in equity_curves and len(equity_curves[h]) > 0:
            ec = equity_curves[h]
            ec_clean = ec.dropna()
            if len(ec_clean) > 0:
                has_data = True
                ax.step(ec_clean.index, ec_clean.values, where='post',
                        color=color, linewidth=0.8, alpha=0.85, label=f'+{h}h')
                ax.fill_between(ec_clean.index, 0, ec_clean.values,
                                where=(ec_clean.values >= 0),
                                color=color, alpha=0.08, step='post')
                ax.fill_between(ec_clean.index, 0, ec_clean.values,
                                where=(ec_clean.values < 0),
                                color=RED, alpha=0.08, step='post')
    if not has_data:
        ax.text(0.5, 0.5, 'No equity data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    ax.axhline(0, color=YELLOW, linewidth=0.8, linestyle='--')
    fmt = mdates.DateFormatter('%Y-%m')
    ax.xaxis.set_major_formatter(fmt)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=7)
    _legend(ax, fontsize=6, labelcolor=TEXT, loc='upper left', ncol=2)
    for h in horizons:
        if h in equity_curves and len(equity_curves[h]) > 0:
            ec = equity_curves[h].dropna()
            if len(ec) > 0:
                total = ec.values[-1]
                color = GREEN if total > 0 else RED
                ax.text(0.02, 0.98, f'+{h}h Total: {total:+.2f}%',
                        transform=ax.transAxes, fontsize=7, color=color,
                        fontweight='bold', va='top')
                break


def _build_panel_r4c3(ax, vol_regime):
    """Volatility Regime Analysis (bar + twin axis)."""
    style_ax(ax, 'Volatility Regime Analysis (24h)', 'Regime', 'Mean %')
    if vol_regime.empty:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', color=TEXT)
        return
    x = range(len(vol_regime))
    colors = [GREEN if m > 0 else RED for m in vol_regime['mean']]
    ax.bar(x, vol_regime['mean'], width=0.4, color=colors, alpha=0.8, label='Mean')
    for i, (_, row) in enumerate(vol_regime.iterrows()):
        label = f'{row["mean"]:.2f}%\nn={int(row["n"])}'
        if row['p_value'] < 0.05:
            label += '*'
        ax.text(i, row['mean'] + (0.02 if row['mean'] >= 0 else -0.04),
                label, ha='center', fontsize=7, color=TEXT)
    ax2 = ax.twinx()
    ax2.bar([i + 0.4 for i in x], vol_regime['excess_vs_random'],
            width=0.4, color=PURPLE, alpha=0.5, label='Excess vs Random')
    ax2.set_ylabel('Excess vs Random %', color=PURPLE, fontsize=8)
    ax2.tick_params(colors=PURPLE, labelsize=7)
    ax2.spines['right'].set_color(PURPLE)
    ax2.spines['top'].set_visible(False)
    ax.set_xticks([i + 0.2 for i in x])
    ax.set_xticklabels(vol_regime['regime'], fontsize=8, color=TEXT)
    ax.axhline(0, color=GRID, linewidth=0.5)
    _legend(ax, fontsize=7, labelcolor=TEXT, loc='upper left')
    _legend(ax2, fontsize=7, labelcolor=TEXT, loc='upper right')


def _build_panel_r5c1(ax, horizon_stats, horizons):
    """Tail Analysis P5/P95 by Horizon (grouped bar)."""
    style_ax(ax, 'Tail Analysis P5/P95 by Horizon', 'Horizon', 'Return %')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    p5 = [h.get('p5', 0) or 0 for h in hs]
    p95 = [h.get('p95', 0) or 0 for h in hs]
    x = range(len(hs))
    w = 0.3
    ax.bar([i - w / 2 for i in x], p5, width=w, color=RED, alpha=0.7, label='P5')
    ax.bar([i + w / 2 for i in x], p95, width=w, color=GREEN, alpha=0.7, label='P95')
    ax.axhline(0, color=GRID, linewidth=0.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(HORIZON_LABELS[:len(hs)], fontsize=7, color=TEXT)
    _legend(ax, fontsize=7, labelcolor=TEXT)


def _build_panel_r5c2(ax, horizon_stats, horizons):
    """Return Skewness by Horizon."""
    style_ax(ax, 'Return Skewness by Horizon', 'Horizon', 'Skewness')
    hs = [horizon_stats.get(h, {}) for h in horizons]
    skew = [h.get('skew', 0) or 0 for h in hs]
    colors = [GREEN if s > 0 else RED for s in skew]
    ax.bar(range(len(skew)), skew, color=colors, alpha=0.8, width=0.6,
           edgecolor='white', linewidth=0.5)
    ax.axhline(0, color=GRID, linewidth=0.5)
    ax.set_xticks(range(len(skew)))
    ax.set_xticklabels(HORIZON_LABELS[:len(skew)], fontsize=7, color=TEXT)
    for i, v in enumerate(skew):
        ax.text(i, v + (0.02 if v >= 0 else -0.04), f'{v:.3f}',
                ha='center', fontsize=7, color=GREEN if v > 0 else RED)


def _build_panel_r5c3(ax, signal_rets, all_rets, horizon_label='1h'):
    """Return Distribution Signal vs All (1h)."""
    style_ax(ax, f'Signal vs Random ({horizon_label})', 'Return %', 'Density')
    bins = np.linspace(-4, 4, 60)
    if len(all_rets) > 2:
        ax.hist(all_rets, bins=bins, alpha=0.35, color=ALL_COLOR, density=True, label='All')
    if len(signal_rets) > 2:
        ax.hist(signal_rets, bins=bins, alpha=0.5, color=SIGNAL_COLOR, density=True, label='Signal')
    ax.axvline(0, color=YELLOW, linewidth=0.8, linestyle='--')
    _legend(ax, fontsize=7, labelcolor=TEXT, loc='upper right')


def _build_panel_r6(ax, analysis, signal_name, horizons):
    """Conclusion / Summary Table."""
    ax.set_facecolor(PANEL)
    ax.axis('off')
    hs = analysis['horizon_stats']
    rolling = analysis['rolling']
    yearly = analysis['yearly']

    best_h = analysis.get('best_horizon')
    best_s = hs.get(best_h, {}) if best_h else hs.get(24, {})

    t_significant = sum(1 for h in horizons
                        if (hs.get(h, {}).get('mean') or 0) > 0
                        and hs.get(h, {}).get('t_p', 1) is not None
                        and hs.get(h, {}).get('t_p', 1) < 0.05)
    mc_significant = sum(1 for h in horizons
                         if (hs.get(h, {}).get('mean') or 0) > 0
                         and hs.get(h, {}).get('mc_p', 1) is not None
                         and hs.get(h, {}).get('mc_p', 1) < 0.05)
    ks_significant = sum(1 for h in horizons
                         if (hs.get(h, {}).get('mean') or 0) > 0
                         and hs.get(h, {}).get('ks_p', 1) is not None
                         and hs.get(h, {}).get('ks_p', 1) < 0.05)
    tests_passed = (1 if t_significant > 0 else 0) + (1 if mc_significant > 0 else 0) + (1 if ks_significant > 0 else 0)

    if tests_passed >= 3:
        verdict = 'STRONG EDGE DETECTED'
        border = GREEN
    elif tests_passed >= 2:
        verdict = 'MODERATE EDGE'
        border = YELLOW
    elif tests_passed >= 1:
        verdict = 'WEAK EDGE'
        border = YELLOW
    else:
        verdict = 'NO SIGNIFICANT EDGE'
        border = RED

    h24 = hs.get(24, {})
    rolling_pos = float((rolling['mean'] > 0).mean() * 100) if not rolling.empty else 0
    years_pos = int((yearly['mean'] > 0).sum()) if not yearly.empty else 0
    years_n = len(yearly) if not yearly.empty else 0

    lines = [
        f'Signal: {signal_name}',
        f'Verdict: {verdict}',
        f'',
        f'Total Signals: {analysis.get("signal_count", 0)} ({analysis.get("signal_pct", 0):.1f}% of candles)',
        f'Best Horizon: +{best_h}h' if best_h else 'Best Horizon: N/A',
        f'',
        f'24h Mean: {h24.get("mean", 0):+.4f}% | Median: {h24.get("median", 0):+.4f}% | '
        f'Std: {h24.get("std", 0):.4f}%',
        f'24h Winrate: {h24.get("winrate", 0):.1f}% | Sharpe: {h24.get("sharpe", 0):.4f}',
        f'95% CI: [{h24.get("ci_low", 0):+.4f}%, {h24.get("ci_high", 0):+.4f}%]',
        f'',
        f'Significant horizons — T-test: {t_significant}/8 | MC: {mc_significant}/8 | KS: {ks_significant}/8',
        f'T-test p (best): {h24.get("t_p", 1):.4f} {"***" if h24.get("t_p", 1) < 0.001 else "**" if h24.get("t_p", 1) < 0.01 else "*" if h24.get("t_p", 1) < 0.05 else ""}',
        f'MC p (best): {h24.get("mc_p", 1):.4f} {"***" if h24.get("mc_p", 1) < 0.001 else "**" if h24.get("mc_p", 1) < 0.01 else "*" if h24.get("mc_p", 1) < 0.05 else ""}',
        f'',
        f'Rolling windows positive: {rolling_pos:.1f}%',
        f'Years positive: {years_pos}/{years_n}',
        f'',
        f'Note: Costs & slippage not included.',
    ]

    for i, line in enumerate(lines):
        y = 0.95 - i * 0.055
        if y < 0:
            break
        if 'Verdict:' in line:
            ax.text(0.02, y, line, transform=ax.transAxes, fontsize=9,
                    color=border, fontweight='bold', fontfamily='monospace')
        elif line.startswith('Note'):
            ax.text(0.02, y, line, transform=ax.transAxes, fontsize=7,
                    color=YELLOW, fontfamily='monospace')
        elif line == '':
            continue
        else:
            ax.text(0.02, y, line, transform=ax.transAxes, fontsize=7,
                    color=TEXT, fontfamily='monospace')

    for spine in ax.spines.values():
        spine.set_color(border)
        spine.set_linewidth(2)


def generate_report(analysis: Dict, signal_name: str, output_path: str,
                    horizons: Optional[List[int]] = None):
    if horizons is None:
        horizons = DEFAULT_HORIZONS

    fig = plt.figure(figsize=(29, 38), facecolor=BG)
    gs = gridspec.GridSpec(6, 3, figure=fig, left=0.05, right=0.97, top=0.985,
                           bottom=0.01, hspace=0.25, wspace=0.18)

    horizon_stats = analysis['horizon_stats']
    rolling = analysis['rolling']
    yearly = analysis['yearly']
    vol_regime = analysis['vol_regime']
    equity_curves = analysis['equity_curves']
    signal_rets_by_h = analysis['signal_rets_by_h']
    all_rets_by_h = analysis['all_rets_by_h']

    # Row 1
    _build_panel_r1c1(fig.add_subplot(gs[0, 0]), horizon_stats, horizons)
    _build_panel_r1c2(fig.add_subplot(gs[0, 1]), horizon_stats, horizons)
    _build_panel_r1c3(fig.add_subplot(gs[0, 2]), horizon_stats, horizons)

    # Row 2
    _build_panel_r2c1(fig.add_subplot(gs[1, 0]),
                       signal_rets_by_h.get(24, pd.Series()),
                       all_rets_by_h.get(24, pd.Series()), '24h')
    _build_panel_r2c2(fig.add_subplot(gs[1, 1]),
                       signal_rets_by_h.get(24, pd.Series()),
                       all_rets_by_h.get(24, pd.Series()), '24h')
    _build_panel_r2c3(fig.add_subplot(gs[1, 2]), horizon_stats, horizons)

    # Row 3
    _build_panel_r3c1(fig.add_subplot(gs[2, 0]), rolling)
    _build_panel_r3c2(fig.add_subplot(gs[2, 1]), rolling)
    _build_panel_r3c3(fig.add_subplot(gs[2, 2]), yearly)

    # Row 4: Cumulative PnL spans cols 0-1, Vol Regime in col 2
    _build_panel_r4c12(fig.add_subplot(gs[3, 0:2]), equity_curves, horizons)
    _build_panel_r4c3(fig.add_subplot(gs[3, 2]), vol_regime)

    # Row 5
    _build_panel_r5c1(fig.add_subplot(gs[4, 0]), horizon_stats, horizons)
    _build_panel_r5c2(fig.add_subplot(gs[4, 1]), horizon_stats, horizons)
    _build_panel_r5c3(fig.add_subplot(gs[4, 2]),
                       signal_rets_by_h.get(1, pd.Series()),
                       all_rets_by_h.get(1, pd.Series()), '1h')

    # Row 6: Conclusion (full width)
    _build_panel_r6(fig.add_subplot(gs[5, :]), analysis, signal_name, horizons)

    fig.savefig(output_path, dpi=150, facecolor=BG)
    plt.close(fig)


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
        mean = s.get('mean') or 0
        t_p = s.get('t_p', np.nan)
        ks_p = s.get('ks_p', np.nan)
        mc_p = s.get('mc_p', np.nan)
        # Only count significance for horizons with positive mean returns
        if mean > 0:
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


def analyze_edge(df: pd.DataFrame, signal_col: str = 'signal',
                 signal_name: str = 'Edge',
                 output_path: str = 'edge_analysis_report.png',
                 horizons: Optional[List[int]] = None,
                 source_file: str = '',
                 quick: bool = False):
    if horizons is None:
        horizons = DEFAULT_HORIZONS
    if signal_col not in df.columns:
        has_fwd = any(c.startswith('fwd_') for c in df.columns)
        if not has_fwd:
            df = df.copy()
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
