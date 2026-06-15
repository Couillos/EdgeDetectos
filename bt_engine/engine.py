"""
BacktestEngine class for running edges against historical data.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple
from edge_registry import Edge

class BacktestEngine:
    def __init__(self, df):
        self.df = df

    def run_edge(self, edge):
        max_h = max(edge.close_horizons)
        if max_h >= len(self.df):
            raise ValueError(f"Max horizon {max_h} exceeds data length {len(self.df)}")
        signals = edge.entry_condition(self.df)
        n_long = (signals == 1).sum(); n_short = (signals == -1).sum()
        print(f"[backtest] {edge.name}: {n_long + n_short} signals ({n_long}L / {n_short}S)")
        equity_curves = {}
        max_entry = len(self.df) - max_h
        for h in edge.close_horizons:
            returns, timestamps = [], []
            for i in range(max_entry):
                sig = signals.iloc[i]
                if sig == 0: continue
                entry_price = self.df.iloc[i]['close']
                exit_price = self.df.iloc[i + h]['close']
                ret = (exit_price - entry_price) / entry_price if sig == 1 else (entry_price - exit_price) / entry_price
                returns.append(ret); timestamps.append(self.df.index[i])
            equity_curves[h] = pd.Series(np.cumsum(returns), index=timestamps, name=f"h={h}") if returns else pd.Series(dtype=float)
        return equity_curves

    def edge_stats(self, edge, equity_curves):
        stats = {}
        for h, curve in equity_curves.items():
            if len(curve) < 2: stats[h] = {'trades': 0}; continue
            rets = curve.diff().fillna(0); total = curve.iloc[-1] if len(curve) > 0 else 0
            wins = (rets > 0).sum(); losses = (rets < 0).sum()
            win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            avg_win = rets[rets > 0].mean() if wins > 0 else 0
            avg_loss = rets[rets < 0].mean() if losses > 0 else 0
            pf = abs(avg_win * wins / (avg_loss * losses)) if avg_loss != 0 and losses > 0 else float('inf')
            sharpe = rets.mean() / rets.std() * np.sqrt(365 * 24 / h) if rets.std() > 0 else 0
            max_dd = (curve.cummax() - curve).max()
            stats[h] = {'trades': len(curve), 'total_return': total, 'win_rate': win_rate,
                        'avg_win': avg_win, 'avg_loss': avg_loss, 'profit_factor': pf,
                        'sharpe': sharpe, 'max_drawdown': max_dd}
        return stats

EDGE_COLORS = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0',
               '#00BCD4', '#FF5722', '#607D8B', '#795548', '#3F51B5']

def generate_legacy_report(edges_results, output_path="backtest_report.png", title="BTC Backtest Report"):
    n_edges = len(edges_results)
    if n_edges == 0: return
    fig = plt.figure(figsize=(16, 4 * n_edges + 1))
    gs = fig.add_gridspec(n_edges + 1, 1, height_ratios=[0.5] + [4] * n_edges, hspace=0.3)
    ax_title = fig.add_subplot(gs[0]); ax_title.axis('off')
    ax_title.text(0.5, 0.5, title, fontsize=16, fontweight='bold', ha='center', va='center', transform=ax_title.transAxes)
    for idx, (edge, equity_curves) in enumerate(edges_results):
        ax = fig.add_subplot(gs[idx + 1])
        color = EDGE_COLORS[idx % len(EDGE_COLORS)]
        ax.set_title(f"Edge: {edge.name}", fontsize=13, fontweight='bold', loc='left')
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.4, linewidth=0.8)
        for h_idx, (h, curve) in enumerate(sorted(equity_curves.items())):
            if len(curve) == 0: continue
            alpha = 0.4 + 0.6 * (h_idx / max(len(equity_curves) - 1, 1))
            ax.plot(curve.index, curve.values, label=f"Close +{h}h", linewidth=1.5, alpha=alpha, color=color)
        y_offsets = [0.98 - 0.045 * i for i in range(len(equity_curves))]
        for i, (h, curve) in enumerate(sorted(equity_curves.items())):
            if len(curve) < 2: continue
            rets = curve.diff().fillna(0); total = curve.iloc[-1]
            wr = (rets > 0).sum() / max((rets != 0).sum(), 1) * 100
            ax.text(0.02, y_offsets[i], f"h={h:2d}: {total:+.2%}  ({len(curve)} trades, {wr:.0f}% WR)",
                    transform=ax.transAxes, fontsize=8, fontfamily='monospace', verticalalignment='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        ax.legend(fontsize=8, loc='upper right'); ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=120, bbox_inches='tight'); plt.close(fig)
    print(f"[report] Saved to {output_path}")

def generate_edge_report(edge, equity_curves, stats, output_path):
    fig = plt.figure(figsize=(12, 6))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    ax_main = fig.add_subplot(gs[:, 0])
    ax_main.set_title(f"Edge: {edge.name}", fontsize=14, fontweight='bold')
    ax_main.axhline(y=0, color='gray', linestyle='--', alpha=0.4)
    for h_idx, (h, curve) in enumerate(sorted(equity_curves.items())):
        if len(curve) == 0: continue
        color = EDGE_COLORS[h_idx % len(EDGE_COLORS)]
        ax_main.plot(curve.index, curve.values, label=f"Close +{h}h", linewidth=1.5, color=color)
    ax_main.legend(fontsize=8); ax_main.grid(True, alpha=0.3)
    ax_stats = fig.add_subplot(gs[0, 1]); ax_stats.axis('off')
    lines = [f"Edge: {edge.name}", f"Horizons: {edge.close_horizons}", ""]
    for h in sorted(stats.keys()):
        s = stats[h]
        if s['trades'] == 0: continue
        lines.append(f"+{h}h: Trades={s['trades']} Return={s['total_return']:.2%} WR={s['win_rate']:.1f}% Sharpe={s['sharpe']:.2f} MaxDD={s['max_drawdown']:.2%}")
    ax_stats.text(0.05, 0.95, "\n".join(lines), transform=ax_stats.transAxes, fontsize=9, fontfamily='monospace', verticalalignment='top')
    ax_dist = fig.add_subplot(gs[1, 1]); ax_dist.set_title("Return Distribution", fontsize=11)
    for h_idx, (h, curve) in enumerate(sorted(equity_curves.items())):
        if len(curve) < 2: continue
        rets = curve.diff().fillna(0)
        ax_dist.hist(rets, bins=30, alpha=0.5, color=EDGE_COLORS[h_idx % len(EDGE_COLORS)], label=f"+{h}h", density=True)
    ax_dist.axvline(0, color='gray', linestyle='--', alpha=0.4); ax_dist.legend(fontsize=7); ax_dist.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=120, bbox_inches='tight'); plt.close(fig)
