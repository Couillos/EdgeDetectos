"""
OOSValidator: runs OOS validation across all edges, generates summary.
"""

import json, os, time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from multiprocessing import Pool

from validation.worker import _oos_worker, SPLIT_DATE, DEFAULT_HORIZONS

VERDICT_STRONG = 70
VERDICT_PASS = 45
VERDICT_WEAK = 25


class OOSValidator:
    def __init__(self, split_date: str = SPLIT_DATE,
                 horizons: Optional[List[int]] = None):
        self.split_date = split_date
        self.horizons = horizons or DEFAULT_HORIZONS

    def validate_all(self, df: pd.DataFrame, reports_dir: str,
                     bt_path: str, sm_path: str,
                     n_workers: Optional[int] = None,
                     quick: bool = True,
                     progress_callback=None,
                     oos_reports_dir: str = '') -> List[Dict]:
        df_oos = df[df.index >= self.split_date].copy()
        tmp_dir = Path('/tmp/oos_validation')
        tmp_dir.mkdir(parents=True, exist_ok=True)
        oos_parquet = str(tmp_dir / 'oos_data.parquet')
        df_oos.to_parquet(oos_parquet)

        reports_path = Path(reports_dir)
        edge_names = []
        for subdir in sorted(reports_path.iterdir()):
            jf = subdir / 'analysis.json'
            if jf.exists():
                with open(jf) as f:
                    edge_names.append(json.load(f)['signal_name'])

        print(f"[oos] Validating {len(edge_names)} edges...")
        n_workers = n_workers or os.cpu_count() or 4

        t0 = time.time()
        results = []
        with Pool(n_workers) as pool:
            args_list = [(name, oos_parquet, bt_path, sm_path,
                          reports_dir, self.split_date,
                          self.horizons, quick, oos_reports_dir)
                         for name in edge_names]
            for i, result in enumerate(pool.imap_unordered(_oos_worker, args_list), 1):
                elapsed = time.time() - t0
                print(f"[oos {i}/{len(edge_names)}] {result.get('verdict','?'):8s} "
                      f"{result.get('edge_name','?'):40s} "
                      f"decay={result.get('decay',{}).get('composite_decay',0):.2f} "
                      f"({elapsed:.0f}s)")
                results.append(result)
                if progress_callback:
                    progress_callback(i, result)

        try: os.remove(oos_parquet)
        except: pass

        print(f"\n[oos] All {len(results)} edges validated in {time.time()-t0:.0f}s")
        return results

    def generate_summary(self, results: List[Dict],
                         symbol: str,
                         output_path: str = 'oos_summary.txt'):
        lines = []
        lines.append('=' * 70)
        lines.append(f'OOS Validation Report — {pd.Timestamp.now().strftime("%Y-%m-%d")}')
        lines.append(f'Symbol: {symbol}')
        lines.append(f'IS: 2020-01-01 → {self.split_date}')
        lines.append(f'OOS: {self.split_date} → now')
        lines.append('=' * 70)
        lines.append('')

        verdicts = {'STRONG': 0, 'PASS': 0, 'WEAK': 0, 'FAIL': 0}
        for r in results:
            v = r.get('verdict', 'FAIL')
            verdicts[v] = verdicts.get(v, 0) + 1

        total = len(results)
        lines.append('VERDICT DISTRIBUTION:')
        for v in ['STRONG', 'PASS', 'WEAK', 'FAIL']:
            pct = verdicts[v] / total * 100 if total > 0 else 0
            bar = '█' * int(pct / 2) + '░' * (50 - int(pct / 2))
            lines.append(f'  {v:8s} {bar} {verdicts[v]:3d} ({pct:5.1f}%)')
        lines.append(f'  {"":8s} {"─" * 50}')
        lines.append(f'  {"Total":8s} {total:3d}')
        lines.append('')

        sorted_results = sorted(results, key=lambda r: r.get('final_score', 0), reverse=True)

        lines.append('TOP 20 EDGES (by final score):')
        lines.append(f'  {"#":<4} {"Name":<40} {"Verdict":<8} {"IS Sc":<6} {"OOS Sc":<6} '
                     f'{"Decay":<6} {"OOS Sh":<7} {"OOS T-p":<8}')
        lines.append('  ' + '-' * 90)
        for i, r in enumerate(sorted_results[:20], 1):
            d = r.get('decay', {})
            oos = r.get('oos', {})
            bs = oos.get('best_stats', {})
            lines.append(f'  {i:<4} {r["edge_name"][:38]:<40} '
                         f'{r.get("verdict","?"):<8} '
                         f'{r.get("is_score",0):<6.1f} '
                         f'{r.get("oos_score",0):<6.1f} '
                         f'{d.get("composite_decay",0):<6.2f} '
                         f'{bs.get("sharpe",0):<+7.4f} '
                         f'{bs.get("t_p",1):<8.4f}')
        lines.append('')

        lines.append('BOTTOM 10 FAILURES:')
        failed = [r for r in sorted_results if r.get('verdict') == 'FAIL'][:10]
        for i, r in enumerate(failed, 1):
            d = r.get('decay', {})
            lines.append(f'  {i:<4} {r["edge_name"][:38]:<40} '
                         f'decay={d.get("composite_decay",0):.2f} '
                         f'{r.get("verdict_detail","")}')
        lines.append('')

        decays = [r.get('decay', {}).get('composite_decay', 1) for r in results]
        lines.append('DECAY ANALYSIS:')
        lines.append(f'  Mean composite decay:  {np.mean(decays):.3f}')
        lines.append(f'  Median composite decay: {np.median(decays):.3f}')
        lines.append(f'  % edges decay > 0.5:    {np.mean(np.array(decays) > 0.5) * 100:.1f}%')
        lines.append(f'  % edges decay > 0.8:    {np.mean(np.array(decays) > 0.8) * 100:.1f}%')
        lines.append('')

        ks_sig = sum(1 for r in results if r.get('is_vs_oos', {}).get('ks_test', {}).get('p_value', 1) < 0.05)
        welch_sig = sum(1 for r in results if r.get('is_vs_oos', {}).get('welch_t_test', {}).get('p_value', 1) < 0.05)
        lev_sig = sum(1 for r in results if r.get('is_vs_oos', {}).get('levene_test', {}).get('p_value', 1) < 0.05)
        lines.append('STATISTICAL TESTS (IS vs OOS):')
        lines.append(f'  % edges with significant KS test (p<0.05):    {ks_sig / total * 100:.1f}%')
        lines.append(f'  % edges with significant Welch t-test (p<0.05): {welch_sig / total * 100:.1f}%')
        lines.append(f'  % edges with significant Levene test (p<0.05): {lev_sig / total * 100:.1f}%')
        lines.append('')
        lines.append('=' * 70)

        if output_path:
            with open(output_path, 'w') as f:
                f.write('\n'.join(lines))
            print(f'[oos] Summary saved to {output_path}')

    def save_csv(self, results: List[Dict], output_path: str = 'oos_ranking.csv'):
        rows = []
        for r in sorted(results, key=lambda x: x.get('final_score', 0), reverse=True):
            d = r.get('decay', {})
            oos = r.get('oos', {}).get('best_stats', {})
            is_best = r.get('is', {}).get('best_stats', {})
            rows.append({
                'edge_name': r['edge_name'],
                'verdict': r.get('verdict', 'FAIL'),
                'is_score': round(r.get('is_score', 0), 2),
                'oos_score': round(r.get('oos_score', 0), 2),
                'final_score': round(r.get('final_score', 0), 2),
                'composite_decay': round(d.get('composite_decay', 1), 4),
                'sharpe_decay': round(d.get('sharpe_decay', 1), 4),
                'mean_decay': round(d.get('mean_decay', 1), 4),
                'dist_ks_p': d.get('dist_ks_p', ''),
                'oos_sharpe': round(oos.get('sharpe', 0), 4),
                'oos_mean': round(oos.get('mean', 0), 4),
                'oos_winrate': round(oos.get('winrate', 0), 2),
                'oos_t_p': round(oos.get('t_p', 1), 4),
                'oos_mc_p': round(oos.get('mc_p', 1), 4),
                'is_sharpe': round(is_best.get('sharpe', 0), 4),
                'is_mean': round(is_best.get('mean', 0), 4),
                'is_winrate': round(is_best.get('winrate', 0), 2),
            })
        pd.DataFrame(rows).to_csv(output_path, index=False)
        print(f'[oos] CSV saved to {output_path}')
