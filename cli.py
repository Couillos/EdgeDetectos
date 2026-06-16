"""
CLI: argparse and dispatch for the edge generator.
"""

import argparse, json, os, re, sys, textwrap, time
from pathlib import Path
from multiprocessing import Pool
from functools import partial
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')

from edge_registry import Edge, register_edge, get_edge, list_edges, _registry, ConditionFn
from bt_engine.data import load_data, register_example_edges, load_user_edges
from bt_engine.engine import BacktestEngine, generate_legacy_report, generate_edge_report
from bt_engine.worker import _mp_run_edge, set_shared_df
from analysis.ranking import generate_ranking
from analysis.report import analyze_edge
from engine.evaluator import generate_edge_file, list_indicators
from engine.indicators import INDICATORS


def main():
    parser = argparse.ArgumentParser(
        description="BTC Backtest Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Available edges:
              Use --list-edges to show all registered edges.
              Add custom edges in edges/*.py.
        """)
    )
    parser.add_argument("--since", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--until", default="2026-06-13", help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading pair (e.g. BTC/USDT, DOGE/USDT)")
    parser.add_argument("--output", default="backtest_report.png", help="Output image path")
    parser.add_argument("--edge", type=str, default=None, help="Run specific edge by name (default: all)")
    parser.add_argument("--analyze", action="store_true", help="Run full statistical analysis with 15-panel report")
    parser.add_argument("--list-edges", action="store_true", help="List all registered edges and exit")
    parser.add_argument("--ranking", action="store_true", help="Generate ranking chart from all reports")
    parser.add_argument("--oos-validate", action="store_true", help="Run OOS validation on all edges")
    parser.add_argument("--list-indicators", action="store_true", help="List all available formula indicators")
    parser.add_argument("--create-edge", type=str, default=None, metavar='NAME', help="Create a new edge file from formulas")
    parser.add_argument("--long", type=str, default=None, help="Long entry formula (for --create-edge, mutually exclusive with --short)")
    parser.add_argument("--short", type=str, default=None, help="Short entry formula (for --create-edge, mutually exclusive with --long)")
    parser.add_argument("--horizons", type=str, default=None, help="Close horizons (comma-separated, for --create-edge)")
    parser.add_argument("--desc", type=str, default='', help="Edge description (for --create-edge)")
    parser.add_argument("--metric", type=str, default='ohlcv', choices=['ohlcv', 'funding_rate', 'open_interest', 'taker_volume', 'long_short_ratio'],
                        help="Market data metric (for --create-edge, default: ohlcv)")
    parser.add_argument("--timeframe", type=str, default='1h', help="Data timeframe (for --create-edge, default: 1h)")
    parser.add_argument("--force", action="store_true", help="Force re-run even if analysis.json exists")
    parser.add_argument("--workers", type=int, default=None, help="Number of worker processes (default: auto)")
    parser.add_argument("--quick", action="store_true", help="Skip chart generation (JSON only)")
    args = parser.parse_args()

    register_example_edges()
    load_user_edges()

    if args.list_indicators:
        print(list_indicators())
        return

    if args.create_edge:
        if args.long and args.short:
            print('[error] An edge must be either long OR short, not both. Use --long OR --short.')
            sys.exit(1)
        if not args.long and not args.short:
            print('[error] You must specify --long or --short formula.')
            sys.exit(1)
        horizons = [int(h) for h in args.horizons.split(',')] if args.horizons else None
        filepath = generate_edge_file(
            name=args.create_edge,
            long_formula=args.long,
            short_formula=args.short,
            horizons=horizons,
            description=args.desc or '',
            metric=args.metric,
            timeframe=args.timeframe,
        )
        print(f'[create-edge] Created {filepath}')
        print(f'[create-edge] Metric: {args.metric}, Timeframe: {args.timeframe}')
        import_types = {'pd': __import__('pandas'), 'np': __import__('numpy'),
                        'eval_formula': __import__('formula_engine').eval_formula}
        ns = {**import_types, '__builtins__': __builtins__}
        try:
            exec(compile(Path(filepath).read_text(), filepath, 'exec'), ns)
            if 'register' in ns:
                print(f'[create-edge] Edge file validates OK')
            print(f'[create-edge] Run: python backtest.py --edge {repr(args.create_edge)} --analyze')
        except Exception as e:
            print(f'[create-edge] Validation FAILED: {e}')
        return

    if args.ranking:
        sym_dir = f'reports_{args.symbol.replace("/", "_")}'
        generate_ranking(ranking_path=f'edge_ranking_{args.symbol.replace("/", "_")}.png',
                         reports_dir=sym_dir)
        return

    if args.oos_validate:
        from validation.core import OOSValidator
        from analysis.core import compute_forward_returns
        sym_dir = f'reports_{args.symbol.replace("/", "_")}'
        validator = OOSValidator()
        df = load_data(since=args.since, until=args.until, symbol=args.symbol)
        df = compute_forward_returns(df, [1, 4, 6, 12, 24, 48, 72, 168])
        bt_path = str(Path(__file__).resolve())
        sm_path = str(Path(f'/tmp/edge_analysis/source_map_{args.symbol.replace("/", "_")}.json'))
        n_workers = args.workers or 12
        results = validator.validate_all(df, sym_dir, bt_path, sm_path, n_workers=n_workers, quick=True)
        out_stem = f'oos_{args.symbol.replace("/", "_")}'
        validator.generate_summary(results, args.symbol, output_path=f'{out_stem}.txt')
        validator.save_csv(results, output_path=f'{out_stem}.csv')
        return

    if args.list_edges:
        print("\nRegistered edges:")
        print("-" * 90)
        print(f"  {'Name':40s} {'Dir':6s} {'Metric':20s} {'TF':6s} {'Horizons':20s}")
        print("  " + "-" * 90)
        for name in sorted(_registry.keys()):
            edge = _registry[name]
            direction = edge.direction[:4]
            metric = edge.metric[:18]
            tf = edge.timeframe
            horiz = ','.join(str(h) for h in edge.close_horizons[:4])
            if len(edge.close_horizons) > 4: horiz += '...'
            print(f"  {name:40s} {direction:6s} {metric:20s} {tf:6s} {horiz:20s}")
        print()
        return

    # Load OHLCV + all available metrics so any edge can reference any column
    if args.analyze:
        extra_metrics = ['funding_rate', 'open_interest', 'taker_volume', 'long_short_ratio']
        print(f'[data] Loading with all extra metrics at {args.timeframe}')
        df = load_data(since=args.since, until=args.until, symbol=args.symbol,
                       metric='ohlcv', timeframe=args.timeframe,
                       extra_metrics=extra_metrics)
    else:
        df = load_data(since=args.since, until=args.until, symbol=args.symbol)
    REPORTS_DIR = f'reports_{args.symbol.replace("/", "_")}'
    HORIZONS = [1, 4, 6, 12, 24, 48, 72, 168]
    from analysis.core import compute_forward_returns
    df = compute_forward_returns(df, HORIZONS)
    print(f"[data] Forward returns computed for {len(HORIZONS)} horizons")

    if args.edge:
        edge = get_edge(args.edge)
        if edge is None:
            print(f"[error] Edge '{args.edge}' not found. Use --list-edges to see available edges.")
            sys.exit(1)
        edges = [edge]
    else:
        edges = list(_registry.values())

    if not edges:
        print("[error] No edges registered.")
        sys.exit(1)

    if args.analyze:
        # Build source file map
        source_map: Dict[str, str] = {}
        edges_dir = Path(__file__).parent / "edges"
        if edges_dir.exists():
            for pyfile in edges_dir.glob("*.py"):
                if pyfile.name == '__init__.py':
                    continue
                try:
                    ns = {'pd': pd, 'np': np, 'register_edge': register_edge,
                          'Edge': Edge, 'ConditionFn': ConditionFn,
                          '__builtins__': __builtins__}
                    with open(pyfile, encoding='utf-8') as f:
                        code = compile(f.read(), pyfile.name, 'exec')
                        exec(code, ns)
                    if 'register' in ns:
                        old_keys = set(_registry.keys())
                        ns['register']()
                        new_keys = set(_registry.keys())
                        for k in new_keys - old_keys:
                            source_map[k] = str(pyfile)
                except Exception:
                    pass

        sym_slug = args.symbol.replace("/", "_")
        tmp_dir = Path('/tmp/edge_analysis')
        tmp_dir.mkdir(parents=True, exist_ok=True)
        df_parquet = str(tmp_dir / f'data_{sym_slug}.parquet')
        df.to_parquet(df_parquet)
        sm_path = str(tmp_dir / f'source_map_{sym_slug}.json')
        with open(sm_path, 'w') as f:
            json.dump(source_map, f)
        edge_names = [e.name for e in edges]
        bt_path = str(Path(__file__).resolve())

        from bt_engine.worker import _optimal_workers
        n_workers = args.workers or _optimal_workers(df, max_workers=os.cpu_count(), quick=args.quick)
        set_shared_df(df)
        print(f"[analyze] Starting {len(edges)} edges with {n_workers} workers...")
        t0 = time.time()
        with Pool(n_workers, maxtasksperchild=1) as pool:
            args_list = [(name, df_parquet, sm_path, args.quick, bt_path, REPORTS_DIR, args.force)
                         for name in edge_names]
            for i, result in enumerate(pool.imap_unordered(_mp_run_edge, args_list), 1):
                elapsed = time.time() - t0
                print(f"[{i}/{len(edges)}] {result} ({elapsed:.0f}s)")

        for f in [df_parquet, sm_path]:
            try: os.remove(f)
            except: pass

        print(f"\n[analyze] All {len(edges)} analyses complete in {time.time()-t0:.0f}s")
        return

    engine = BacktestEngine(df)
    results = []
    for edge in edges:
        equity_curves = engine.run_edge(edge)
        results.append((edge, equity_curves))
        stats = engine.edge_stats(edge, equity_curves)
        safe_name = re.sub(r'[^\w\s-]', '', edge.name).strip().replace(' ', '_').lower()
        edge_path = args.output.replace('.png', f'_{safe_name}.png')
        generate_edge_report(edge, equity_curves, stats, edge_path)

    generate_legacy_report(results, output_path=args.output,
                           title=f"BTC Backtest — {args.since} to {args.until}")

    print("\n" + "=" * 70)
    print(f"{'Edge':30s} {'Horizon':>8s} {'Trades':>7s} {'Return':>10s} {'WR':>6s} {'Sharpe':>8s}")
    print("-" * 70)
    for edge, equity_curves in results:
        stats = engine.edge_stats(edge, equity_curves)
        for h in sorted(stats.keys()):
            s = stats[h]
            if s['trades'] == 0:
                continue
            print(f"{edge.name:30s} {'+'+str(h)+'h':>8s} {s['trades']:7d} "
                  f"{s['total_return']:+9.2%} {s['win_rate']:5.1f}% {s['sharpe']:7.2f}")
    print("=" * 70)
