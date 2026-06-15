"""
Ranking chart generator: reads all analysis.json and produces a ranked bar chart.
"""

import json
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from typing import Dict, List

from analysis.core import DEFAULT_HORIZONS, HORIZON_LABELS

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


def generate_ranking(ranking_path: str = 'edge_ranking.png',
                     reports_dir: str = 'reports'):
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        print(f'[ranking] No reports directory found at {reports_dir}')
        return

    all_data = []
    for subdir in sorted(reports_path.iterdir()):
        jf = subdir / 'analysis.json'
        if not jf.exists():
            continue
        try:
            with open(jf) as f:
                data = json.load(f)
        except Exception:
            continue

        name = data.get('signal_name', subdir.stem)
        best_s = data.get('best_sharpe', 0) or 0
        t_p = data.get('best_t_p', 1) or 1
        ks_p = data.get('best_ks_p', 1) or 1
        mc_p = data.get('best_mc_p', 1) or 1
        wr = data.get('best_winrate', 50) or 50

        # Quality score (matches ranking in stats output)
        sig = 0
        if t_p < 0.05: sig += 1
        if ks_p < 0.05: sig += 1
        if mc_p < 0.05: sig += 1
        breadth = sum(
            1 for h_s in data.get('horizons', {}).values()
            if h_s.get('t_p', 1) < 0.05 and h_s.get('mc_p', 1) < 0.05
        )
        score = sig * 10 + breadth * 3

        all_data.append({
            'name': name, 'score': score, 'sharpe': best_s,
            't_p': t_p, 'ks_p': ks_p, 'mc_p': mc_p,
            'winrate': wr,
        })

    if not all_data:
        print(f'[ranking] No analysis data found in {reports_dir}')
        return

    all_data.sort(key=lambda x: x['score'], reverse=True)
    top_n = min(len(all_data), 40)

    print(f'[ranking] Found {len(all_data)} edges, plotting top {top_n}')

    fig = plt.figure(figsize=(16, max(8, top_n * 0.35)), facecolor=BG)
    gs = gridspec.GridSpec(1, 4, wspace=0.3, left=0.05, right=0.98, top=0.95, bottom=0.08)

    names = [d['name'][:40] for d in all_data[:top_n]][::-1]
    scores = [d['score'] for d in all_data[:top_n]][::-1]
    sharpes = [d['sharpe'] for d in all_data[:top_n]][::-1]
    t_ps = [d['t_p'] for d in all_data[:top_n]][::-1]
    ks_ps = [d['ks_p'] for d in all_data[:top_n]][::-1]
    mc_ps = [d['mc_p'] for d in all_data[:top_n]][::-1]
    wrs = [d['winrate'] for d in all_data[:top_n]][::-1]

    # Score bar chart
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(PANEL)
    colors = [GREEN if s > 20 else YELLOW if s > 10 else RED for s in scores]
    bars = ax1.barh(range(len(names)), scores, color=colors, height=0.7)
    ax1.set_yticks(range(len(names)))
    ax1.set_yticklabels(names, fontsize=7, color=TEXT)
    ax1.set_xlabel('Score', color=TEXT, fontsize=9)
    ax1.tick_params(colors=TEXT, labelsize=7)
    ax1.spines['bottom'].set_color(GRID)
    ax1.spines['left'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(True, axis='x', alpha=0.15, color=GRID)
    for bar, v in zip(bars, scores):
        ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f'{v:.0f}', va='center', fontsize=7, color=TEXT)

    # -log10 p-values
    for idx, (ax_pos, label, values) in enumerate([
        (1, 'T-test', t_ps), (2, 'KS-test', ks_ps), (3, 'Win%', wrs)
    ]):
        ax = fig.add_subplot(gs[0, ax_pos])
        ax.set_facecolor(PANEL)
        neg_log = [-np.log10(max(v, 1e-10)) for v in values]
        colors = [GREEN if nl > 1.3 else YELLOW if nl > 0.7 else RED for nl in neg_log]
        ax.barh(range(len(names)), neg_log, color=colors, height=0.7)
        ax.set_yticks([])
        ax.set_xlabel(label, color=TEXT, fontsize=9)
        ax.tick_params(colors=TEXT, labelsize=7)
        ax.spines['bottom'].set_color(GRID)
        ax.spines['left'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, axis='x', alpha=0.15, color=GRID)
        ax.axvline(-np.log10(0.05), color=YELLOW, linewidth=0.6, linestyle='--', alpha=0.6)

    fig.savefig(ranking_path, dpi=150, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    print(f'[ranking] Saved ranking chart to {ranking_path}')
