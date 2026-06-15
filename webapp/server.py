"""
Edge Generator — FastAPI Backend
Serves GET endpoints for edge listing, indicators, reports, ranking, OOS.
POST endpoints for async analysis and edge creation with SSE progress.
"""

import sys, os, json, re, time, uuid, asyncio, concurrent.futures, logging, warnings
from pathlib import Path
from typing import Optional, List
from functools import partial
from contextlib import asynccontextmanager
from urllib.parse import quote, unquote

import pandas as pd
import numpy as np
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse, StreamingResponse, HTMLResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backtest  # noqa: ensures backtest.py is importable for workers
from edge_registry import _registry, get_edge, Edge, register_edge, ConditionFn
from bt_engine.data import load_data, register_example_edges, load_user_edges
from bt_engine.worker import _mp_run_edge, set_shared_df, _optimal_workers
from analysis.core import compute_forward_returns, DEFAULT_HORIZONS
from engine.indicators import INDICATORS
from engine.evaluator import generate_edge_file
from validation.core import OOSValidator
from validation.worker import SPLIT_DATE

logging.basicConfig(level=logging.INFO, format='[server] %(message)s')
log = logging.getLogger(__name__)

# File logging for warnings and errors
_log_dir = PROJECT_ROOT / 'logs'
_log_dir.mkdir(parents=True, exist_ok=True)
_fh_warn = logging.FileHandler(str(_log_dir / 'warning.log'), encoding='utf-8')
_fh_warn.setLevel(logging.WARNING)
_fh_warn.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
_fh_err = logging.FileHandler(str(_log_dir / 'error.log'), encoding='utf-8')
_fh_err.setLevel(logging.ERROR)
_fh_err.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(_fh_warn)
logging.getLogger().addHandler(_fh_err)
logging.captureWarnings(True)


# ─── Startup ───────────────────────────────────────────────────────────

SYMBOLS: List[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Registering edges...")
    register_example_edges()
    load_user_edges()
    log.info(f"Registry has {len(_registry)} edges")

    global SYMBOLS
    for d in PROJECT_ROOT.iterdir():
        if d.name.startswith('reports_') and d.is_dir():
            sym = d.name[len('reports_'):].replace('_', '/', 1)
            SYMBOLS.append(sym)
    SYMBOLS = sorted(set(SYMBOLS))
    log.info(f"Found symbols: {SYMBOLS}")

    _init_analysis_cache()
    for sym in SYMBOLS:
        log.info(f"Warming cache for {sym}...")
        _rebuild_cache_for_symbol(sym)
    log.info(f"Cache warmed: {sum(len(v) for v in _edges_cache.values())} entries across {len(_edges_cache)} symbols")
    yield


app = FastAPI(title="Edge Generator API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

WEBAPP_ROOT = Path(__file__).parent


@app.get('/')
@app.head('/')
def serve_index():
    return HTMLResponse((WEBAPP_ROOT / 'templates' / 'index.html').read_text())


# ─── Helpers ───────────────────────────────────────────────────────────

BT_PATH = str(PROJECT_ROOT / 'backtest.py')
HORIZONS = [1, 4, 6, 12, 24, 48, 72, 168]


def _safe_name(name: str) -> str:
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_').lower()


def _symbol_slug(symbol: str) -> str:
    return symbol.replace('/', '_')


def _reports_dir(symbol: str) -> str:
    return f'reports_{_symbol_slug(symbol)}'


def _clean_nan(v, default=None):
    """Convert NaN/Inf to default (None for JSON safety)."""
    if v is None:
        return default
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return default
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return default
    return v


def _safe_round(v, ndigits=2):
    """Round safely — returns NaN as-is (to be cleaned by _clean_json later)."""
    if v is None:
        return None
    try:
        return round(float(v), ndigits)
    except (ValueError, TypeError):
        return None


def _clean_json(obj):
    """Recursively replace NaN/Inf with None in JSON-serializable structures."""
    if isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_json(v) for v in obj]
    return _clean_nan(obj)


def _read_analysis_json(name: str, symbol: str) -> Optional[dict]:
    rd = _reports_dir(symbol)
    path = Path(PROJECT_ROOT / rd / _safe_name(name) / 'analysis.json')
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return None


def _read_analysis_json_for_edge(edge_name: str, symbol: str) -> Optional[dict]:
    # Try all symbols if symbol not specified
    syms = [symbol] if symbol else SYMBOLS
    for sym in syms:
        aj = _read_analysis_json(edge_name, sym)
        if aj:
            return aj
    return None


def _edge_report_json_url(name: str) -> str:
    return f'/api/report/{quote(name)}/json'


def _edge_report_png_url(name: str) -> str:
    return f'/api/report/{quote(name)}/png'


# ─── Cache ─────────────────────────────────────────────────────────────

import time as _time

_edges_cache: dict = {}
_edges_cache_time: float = 0
_CACHE_TTL = 30  # seconds


def _init_analysis_cache():
    global _edges_cache, _edges_cache_time
    _edges_cache = {}
    _edges_cache_time = 0


def _rebuild_cache_for_symbol(symbol: str):
    global _edges_cache, _edges_cache_time
    cache = {}
    for name in _registry:
        aj = _read_analysis_json(name, symbol)
        if aj:
            cache[name] = aj
    if symbol not in _edges_cache:
        _edges_cache[symbol] = {}
    _edges_cache[symbol].update(cache)
    _edges_cache_time = _time.time()


def _get_cached_analysis(name: str, symbol: str) -> Optional[dict]:
    global _edges_cache, _edges_cache_time
    now = _time.time()
    sym_cache = _edges_cache.get(symbol)
    if sym_cache is None or now - _edges_cache_time > _CACHE_TTL:
        _rebuild_cache_for_symbol(symbol)
        sym_cache = _edges_cache.get(symbol, {})
    return sym_cache.get(name)


def _build_edge_list(symbol: str, search: str = '', status: str = 'all',
                     sort: str = 'name', order: str = 'asc'):
    # Warm cache on first call
    now = _time.time()
    if symbol not in _edges_cache or now - _edges_cache_time > _CACHE_TTL:
        _rebuild_cache_for_symbol(symbol)

    sym_cache = _edges_cache.get(symbol, {})
    edges = []
    for name, edge in _registry.items():
        if search and search.lower() not in name.lower():
            continue
        aj = sym_cache.get(name)
        has_analysis = aj is not None
        if status == 'analyzed' and not has_analysis:
            continue
        if status == 'pending' and has_analysis:
            continue

        best_verdict = aj['verdict'] if aj else ''
        best_sharpe = aj.get('best_sharpe', 0) or 0 if aj else None
        best_winrate = aj.get('best_winrate', 0) or 0 if aj else None
        total_signals = aj.get('total_signals', 0) if aj else 0

        edges.append({
            'name': name,
            'description': edge.description or '',
            'signal_type': 'both',
            'has_analysis': has_analysis,
            'verdict': best_verdict or '',
            'best_sharpe': _clean_nan(round(best_sharpe, 4)) if best_sharpe is not None else None,
            'best_winrate': _clean_nan(round(best_winrate, 2)) if best_winrate is not None else None,
            'total_signals': total_signals or 0,
            'report_json': _edge_report_json_url(name) if has_analysis else None,
            'report_png': _edge_report_png_url(name) if has_analysis else None,
        })

    reverse = order == 'desc'
    if sort == 'name':
        edges.sort(key=lambda e: e['name'].lower(), reverse=reverse)
    elif sort == 'sharpe':
        edges.sort(key=lambda e: e['best_sharpe'] if e['best_sharpe'] is not None else -999, reverse=not reverse)
    elif sort == 'winrate':
        edges.sort(key=lambda e: e['best_winrate'] if e['best_winrate'] is not None else -999, reverse=not reverse)

    return edges


# ─── Pydantic Models ──────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol: str = 'BTC/USDT'
    symbols: str = ''
    since: str = '2020-01-01'
    until: str = '2026-06-13'
    edge_name: Optional[str] = None
    quick: bool = False
    force: bool = False


class OOSValidateRequest(BaseModel):
    symbol: str = 'BTC/USDT'
    since: str = '2020-01-01'
    until: str = '2026-06-13'


class CreateEdgeRequest(BaseModel):
    name: str
    long_formula: str
    short_formula: Optional[str] = None
    horizons: str = '1,4,6,12,24,48,72,168'
    description: str = ''


# ─── GET /api/edges ───────────────────────────────────────────────────

@app.get('/api/edges')
def list_edges(
    search: str = '',
    sort: str = 'name',
    order: str = 'asc',
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=2000),
    status: str = 'all',
    symbol: str = 'BTC/USDT',
):
    symbol = symbol.replace('%2F', '/')
    edges = _build_edge_list(symbol, search, status, sort, order)
    total = len(edges)
    start = (page - 1) * per_page
    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'edges': edges[start:start + per_page],
    }


# ─── GET /api/indicators ──────────────────────────────────────────────

@app.get('/api/indicators')
def list_indicators():
    cats = {}
    for name, info in INDICATORS.items():
        cat = info['category'] or 'Other'
        cats.setdefault(cat, []).append(name)
    return {'total': len(INDICATORS), 'categories': cats}


# ─── GET /api/edges/{name} ────────────────────────────────────────────

@app.get('/api/edges/{name:path}')
def edge_detail(name: str, symbol: str = 'BTC/USDT'):
    name = unquote(name)
    edge = get_edge(name)
    if not edge:
        raise HTTPException(404, f"Edge '{name}' not found")

    aj = _read_analysis_json(name, symbol)
    if not aj:
        return {
            'signal_name': name,
            'description': edge.description,
            'source_file': '',
            'has_analysis': False,
        }

    aj['description'] = edge.description
    aj['report_json'] = _edge_report_json_url(name)
    aj['report_png'] = _edge_report_png_url(name)
    aj['has_analysis'] = True
    return _clean_json(aj)


# ─── GET /api/report/{name}/json ──────────────────────────────────────

@app.get('/api/report/{name:path}/json')
def report_json(name: str):
    name = unquote(name)
    for sym in SYMBOLS:
        aj = _read_analysis_json(name, sym)
        if aj:
            return _clean_json(aj)
    raise HTTPException(404, f"No analysis.json for '{name}'")


# ─── GET /api/report/{name}/png ───────────────────────────────────────
# This handler also matches /api/report/{name}/json (more specific above)

@app.get('/api/report/{name:path}/png')
def report_png(name: str, symbol: str = ''):
    name = unquote(name)
    syms = [symbol] if symbol else SYMBOLS
    for sym in syms:
        rd = _reports_dir(sym)
        png_path = PROJECT_ROOT / rd / _safe_name(name) / 'report.png'
        if png_path.exists():
            return FileResponse(str(png_path), media_type='image/png')
    raise HTTPException(404, f"No report.png for '{name}'")


# ─── GET /api/ranking ─────────────────────────────────────────────────

@app.get('/api/ranking')
def ranking(symbol: str = Query('BTC/USDT')):
    sym_slug = _symbol_slug(symbol)
    rd = _reports_dir(symbol)
    reports_path = PROJECT_ROOT / rd
    if not reports_path.exists():
        raise HTTPException(404, f"No reports for {symbol}")

    all_data = []
    for subdir in sorted(reports_path.iterdir()):
        jf = subdir / 'analysis.json'
        if not jf.exists():
            continue
        try:
            data = json.loads(jf.read_text(encoding='utf-8'))
        except Exception:
            continue

        name = data.get('signal_name', subdir.stem)
        best_s = data.get('best_sharpe', 0) or 0
        t_p = data.get('best_t_p', 1) or 1
        mc_p = data.get('best_mc_p', 1) or 1
        wr = data.get('best_winrate', 50) or 50
        total_ret = 0
        for h_s in data.get('horizons', {}).values():
            tr = h_s.get('total_return', 0) or 0
            if abs(tr) > abs(total_ret):
                total_ret = tr

        sig = 0
        if t_p < 0.05:
            sig += 1
        if data.get('best_ks_p', 1) < 0.05:
            sig += 1
        if mc_p < 0.05:
            sig += 1
        breadth = sum(
            1 for h_s in data.get('horizons', {}).values()
            if h_s.get('t_p', 1) < 0.05 and h_s.get('mc_p', 1) < 0.05
        )
        score = sig * 10 + breadth * 3

        verdict = data.get('verdict', 'NONE')
        all_data.append({
            'name': name,
            'score': round(score, 1),
            'sig': sig,
            'breadth': breadth,
            'verdict': verdict,
            'sharpe': _clean_nan(round(best_s, 4)),
            'winrate': _clean_nan(round(wr, 2)),
            'total_return': _clean_nan(round(total_ret, 4)),
            't_p': _clean_nan(t_p),
            'mc_p': _clean_nan(mc_p),
            'ks_p': _clean_nan(data.get('best_ks_p', 1)),
        })

    all_data.sort(key=lambda x: x['score'], reverse=True)

    ranking_png = PROJECT_ROOT / f'edge_ranking_{sym_slug}.png'
    return {
        'edges': all_data,
        'ranking_png': f'/api/ranking/{sym_slug}/png' if ranking_png.exists() else None,
    }


# ─── GET /api/ranking/{symbol_slug}/png ───────────────────────────────

@app.get('/api/ranking/{symbol_slug}/png')
def ranking_png(symbol_slug: str):
    sym = symbol_slug.replace('_', '/')
    path = PROJECT_ROOT / f'edge_ranking_{symbol_slug}.png'
    if not path.exists():
        # Try generating it on the fly
        try:
            from analysis.ranking import generate_ranking
            rd = _reports_dir(sym)
            generate_ranking(ranking_path=str(path), reports_dir=str(PROJECT_ROOT / rd))
        except Exception as e:
            log.warning(f"Could not generate ranking: {e}")
    if not path.exists():
        raise HTTPException(404, f"Ranking PNG not found for {symbol_slug}")
    return FileResponse(str(path), media_type='image/png')


# ─── GET /api/oos/{symbol} ────────────────────────────────────────────

@app.get('/api/oos/{symbol:path}')
def oos_data(symbol: str):
    sym_slug = _symbol_slug(symbol)
    txt_path = PROJECT_ROOT / f'oos_{sym_slug}.txt'
    csv_path = PROJECT_ROOT / f'oos_{sym_slug}.csv'

    if not csv_path.exists():
        raise HTTPException(404, f"No OOS data for {symbol}")

    df = pd.read_csv(str(csv_path))
    verdicts = df['verdict'].value_counts().to_dict()
    for v in ['STRONG', 'PASS', 'WEAK', 'FAIL']:
        verdicts.setdefault(v, 0)

    edges = []
    for _, row in df.iterrows():
        edges.append({
            'name': _clean_nan(row.get('edge_name', ''), ''),
            'verdict': _clean_nan(row.get('verdict', 'NONE'), 'NONE'),
            'is_score': _clean_nan(_safe_round(row.get('is_score', 0), 2), None),
            'oos_score': _clean_nan(_safe_round(row.get('oos_score', 0), 2), None),
            'final_score': _clean_nan(_safe_round(row.get('final_score', 0), 2), None),
            'decay': _clean_nan(_safe_round(row.get('composite_decay', 1), 4), None),
            'oos_sharpe': _clean_nan(_safe_round(row.get('oos_sharpe', 0), 4), None),
            'oos_winrate': _clean_nan(_safe_round(row.get('oos_winrate', 0), 2), None),
            'oos_t_p': _clean_nan(_safe_round(row.get('oos_t_p', 1), 4), None),
            'oos_mc_p': _clean_nan(_safe_round(row.get('oos_mc_p', 1), 4), None),
            'dist_ks_p': _clean_nan(_safe_round(row.get('dist_ks_p', 1), 4), None),
            'is_sharpe': _clean_nan(_safe_round(row.get('is_sharpe', 0), 4), None),
        })

    return {
        'verdicts': verdicts,
        'edges': edges,
        'txt_summary': txt_path.read_text(encoding='utf-8') if txt_path.exists() else '',
    }


# ─── GET /api/symbols ─────────────────────────────────────────────────

@app.get('/api/symbols')
def get_symbols():
    return SYMBOLS


# ─── Task Management ──────────────────────────────────────────────────

_analysis_tasks: dict = {}
_oos_tasks: dict = {}


# ─── POST /api/analyze ────────────────────────────────────────────────

@app.post('/api/analyze')
async def start_analysis(body: AnalyzeRequest):
    task_id = uuid.uuid4().hex[:12]
    task = {
        'task_id': task_id,
        'status': 'running',
        'total': 0, 'completed': 0, 'skipped': 0, 'failed': 0,
        'start_time': time.time(),
        'updates': [],
        'complete_msg': None,
    }
    _analysis_tasks[task_id] = task
    asyncio.create_task(_run_analysis(task_id, body))
    return {'task_id': task_id, 'status': 'started'}


async def _run_analysis(task_id: str, body: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    task = _analysis_tasks[task_id]

    def _do_analysis():
        symbols = [s.strip() for s in body.symbols.split(',') if s.strip()] if body.symbols else [body.symbol]

        # Build source map once (edges are shared across symbols)
        source_map = {}
        edges_dir = PROJECT_ROOT / "edges"
        if edges_dir.exists():
            for pyfile in sorted(edges_dir.glob("*.py")):
                if pyfile.name == '__init__.py' or pyfile.name.startswith('_'):
                    continue
                try:
                    ns = {'pd': pd, 'np': np, 'register_edge': register_edge,
                          'Edge': Edge, 'ConditionFn': ConditionFn, '__builtins__': __builtins__}
                    code = compile(pyfile.read_text(), pyfile.name, 'exec')
                    exec(code, ns)
                    if 'register' in ns:
                        old_keys = set(_registry.keys())
                        ns['register']()
                        for k in set(_registry.keys()) - old_keys:
                            source_map[k] = str(pyfile)
                except Exception:
                    pass

        if body.edge_name:
            edge = get_edge(body.edge_name)
            edge_names = [edge.name] if edge else []
        else:
            edge_names = list(_registry.keys())

        task['total'] = len(edge_names) * len(symbols)
        if not edge_names or not symbols:
            task['status'] = 'complete'
            task['complete_msg'] = {
                'type': 'complete', 'total': 0, 'completed': 0,
                'skipped': 0, 'failed': 0, 'elapsed': 0,
            }
            return

        tmp_dir = Path('/tmp/edge_analysis')
        tmp_dir.mkdir(parents=True, exist_ok=True)

        for sym_idx, symbol in enumerate(symbols):
            df = load_data(since=body.since, until=body.until, symbol=symbol)
            df = compute_forward_returns(df, HORIZONS)
            sym_slug = _symbol_slug(symbol)
            reports_dir_name = _reports_dir(symbol)
            df_parquet = str(tmp_dir / f'data_{sym_slug}.parquet')
            df.to_parquet(df_parquet)

            sm_path = str(tmp_dir / f'source_map_{sym_slug}.json')
            with open(sm_path, 'w') as f:
                json.dump(source_map, f)

            # Force re-run: delete existing analysis before workers start
            if body.force:
                for ename in edge_names:
                    safe = _safe_name(ename)
                    rep_path = PROJECT_ROOT / reports_dir_name / safe
                    aj_path = rep_path / 'analysis.json'
                    if aj_path.exists():
                        try:
                            aj_path.unlink()
                        except Exception:
                            pass
                    png_path = rep_path / 'report.png'
                    if png_path.exists():
                        try:
                            png_path.unlink()
                        except Exception:
                            pass

            # Share DataFrame via fork inheritance — workers avoid reloading from parquet
            set_shared_df(df)
            n_workers = _optimal_workers(df, max_workers=os.cpu_count())

            with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as pool:
                futs = []
                for ename in edge_names:
                    args = (ename, df_parquet, sm_path, body.quick, BT_PATH, reports_dir_name, body.force)
                    futs.append(pool.submit(_mp_run_edge, tuple(args)))

                for fut in concurrent.futures.as_completed(futs):
                    result = fut.result()
                    elapsed = round(time.time() - task['start_time'], 1)
                    if result.startswith('[done]'):
                        task['completed'] += 1
                        ename = result[6:].strip()
                    elif result.startswith('[skip]'):
                        task['skipped'] += 1
                        ename = result[6:].strip()
                    elif result.startswith('[FAIL]'):
                        task['failed'] += 1
                        ename = result[6:].strip()
                    processed = task['completed'] + task['skipped'] + task['failed']
                    task['updates'].append({
                        'type': 'progress', 'edge_name': f'[{symbol}] {ename}',
                        'completed': task['completed'], 'total': task['total'],
                        'processed': processed, 'status': 'done',
                        'elapsed': elapsed,
                    })

            for f in [df_parquet, sm_path]:
                try:
                    os.remove(f)
                except Exception:
                    pass

        task['status'] = 'complete'
        task['complete_msg'] = {
            'type': 'complete',
            'total': task['total'],
            'completed': task['completed'],
            'skipped': task['skipped'],
            'failed': task['failed'],
            'elapsed': round(time.time() - task['start_time'], 1),
        }
        for sym in symbols:
            _rebuild_cache_for_symbol(sym)

    try:
        await loop.run_in_executor(None, _do_analysis)
    except Exception as e:
        log.error(f"Analysis task {task_id} failed: {e}")
        task['status'] = 'complete'
        task['complete_msg'] = {
            'type': 'complete',
            'total': task.get('total', 0),
            'completed': task.get('completed', 0),
            'skipped': task.get('skipped', 0),
            'failed': task.get('failed', 0),
            'elapsed': round(time.time() - task.get('start_time', time.time()), 1),
            'error': str(e),
        }


# ─── GET /api/analyze/{task_id}/progress ──────────────────────────────

@app.get('/api/analyze/{task_id}/progress')
async def analyze_progress(task_id: str):
    task = _analysis_tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    async def event_generator():
        last_idx = 0
        while True:
            updates = task.get('updates', [])
            while last_idx < len(updates):
                u = updates[last_idx]
                last_idx += 1
                yield f"event: progress\ndata: {json.dumps(u)}\n\n"

            if task['status'] == 'complete':
                if task['complete_msg']:
                    yield f"event: complete\ndata: {json.dumps(task['complete_msg'])}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type='text/event-stream')


# ─── POST /api/oos-validate ──────────────────────────────────────────

@app.post('/api/oos-validate')
async def start_oos_validate(body: OOSValidateRequest):
    task_id = uuid.uuid4().hex[:12]
    task = {
        'task_id': task_id,
        'status': 'running',
        'total': 0, 'completed': 0, 'skipped': 0, 'failed': 0,
        'start_time': time.time(),
        'updates': [],
        'complete_msg': None,
    }
    _oos_tasks[task_id] = task
    asyncio.create_task(_run_oos(task_id, body))
    return {'task_id': task_id, 'status': 'started'}


async def _run_oos(task_id: str, body: OOSValidateRequest):
    loop = asyncio.get_event_loop()
    task = _oos_tasks[task_id]

    def _do_oos():
        sym_slug = _symbol_slug(body.symbol)
        rd = _reports_dir(body.symbol)
        df = load_data(since=body.since, until=body.until, symbol=body.symbol)
        df = compute_forward_returns(df, HORIZONS)
        tmp_dir = Path('/tmp/edge_analysis')
        tmp_dir.mkdir(parents=True, exist_ok=True)
        df_parquet = str(tmp_dir / f'oos_data_{sym_slug}.parquet')
        df.to_parquet(df_parquet)
        sm_path = str(tmp_dir / f'oossm_{sym_slug}.json')

        source_map = {}
        edges_dir = PROJECT_ROOT / "edges"
        if edges_dir.exists():
            for pyfile in sorted(edges_dir.glob("*.py")):
                if pyfile.name == '__init__.py' or pyfile.name.startswith('_'):
                    continue
                try:
                    ns = {'pd': pd, 'np': np, 'register_edge': register_edge,
                          'Edge': Edge, 'ConditionFn': ConditionFn, '__builtins__': __builtins__}
                    code = compile(pyfile.read_text(), pyfile.name, 'exec')
                    exec(code, ns)
                    if 'register' in ns:
                        old_keys = set(_registry.keys())
                        ns['register']()
                        for k in set(_registry.keys()) - old_keys:
                            source_map[k] = str(pyfile)
                except Exception:
                    pass
        with open(sm_path, 'w') as f:
            json.dump(source_map, f)

        validator = OOSValidator()
        reports_path = str(PROJECT_ROOT / rd)
        results = validator.validate_all(df, reports_path, BT_PATH, sm_path,
                                         n_workers=os.cpu_count() or 4, quick=True)

        task['total'] = len(results)
        for i, r in enumerate(results):
            task['completed'] = i + 1
            elapsed = round(time.time() - task['start_time'], 1)
            verdict = r.get('verdict', 'FAIL')
            task['updates'].append({
                'type': 'progress',
                'edge_name': r.get('edge_name', '?'),
                'completed': task['completed'],
                'total': task['total'],
                'status': 'done',
                'verdict': verdict,
                'elapsed': elapsed,
            })

        out_stem = str(PROJECT_ROOT / f'oos_{sym_slug}')
        validator.generate_summary(results, body.symbol, output_path=f'{out_stem}.txt')
        validator.save_csv(results, output_path=f'{out_stem}.csv')

        for f in [df_parquet, sm_path]:
            try:
                os.remove(f)
            except Exception:
                pass

        task['status'] = 'complete'
        task['complete_msg'] = {
            'type': 'complete',
            'total': task['total'],
            'completed': task['completed'],
            'skipped': task['skipped'],
            'failed': task['failed'],
            'elapsed': round(time.time() - task['start_time'], 1),
        }

    try:
        await loop.run_in_executor(None, _do_oos)
    except Exception as e:
        log.error(f"OOS task {task_id} failed: {e}")
        task['status'] = 'complete'
        task['complete_msg'] = {
            'type': 'complete',
            'total': task.get('total', 0),
            'completed': task.get('completed', 0),
            'skipped': 0, 'failed': 0,
            'elapsed': round(time.time() - task.get('start_time', time.time()), 1),
            'error': str(e),
        }


# ─── GET /api/oos-validate/{task_id}/progress ─────────────────────────

@app.get('/api/oos-validate/{task_id}/progress')
async def oos_progress(task_id: str):
    task = _oos_tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    async def event_generator():
        last_idx = 0
        while True:
            updates = task.get('updates', [])
            while last_idx < len(updates):
                u = updates[last_idx]
                last_idx += 1
                yield f"event: progress\ndata: {json.dumps(u)}\n\n"

            if task['status'] == 'complete':
                if task['complete_msg']:
                    yield f"event: complete\ndata: {json.dumps(task['complete_msg'])}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type='text/event-stream')


# ─── POST /api/edges/create ───────────────────────────────────────────

@app.post('/api/edges/create')
def create_edge(body: CreateEdgeRequest):
    try:
        # Validate formulas before generating file
        dummy_df = pd.DataFrame({'close': [100.0], 'high': [101.0], 'low': [99.0], 'open': [100.0], 'volume': [1000]})
        from formula_engine import eval_formula
        try:
            eval_formula(body.long_formula, dummy_df)
        except Exception as e:
            return {'status': 'error', 'error': f'Long formula error: {e}'}
        if body.short_formula:
            try:
                eval_formula(body.short_formula, dummy_df)
            except Exception as e:
                return {'status': 'error', 'error': f'Short formula error: {e}'}

        horizons = [int(h.strip()) for h in body.horizons.split(',') if h.strip()]
        if not horizons:
            return {'status': 'error', 'error': 'At least one horizon required'}

        filepath = generate_edge_file(
            name=body.name,
            long_formula=body.long_formula,
            short_formula=body.short_formula,
            horizons=horizons,
            description=body.description,
        )
        validate_ns = {
            'pd': pd, 'np': np,
            'eval_formula': eval_formula,
            '__builtins__': __builtins__,
        }
        exec(compile(Path(filepath).read_text(), filepath, 'exec'), validate_ns)
        if 'register' in validate_ns:
            log.info(f"Edge '{body.name}' validates OK")

        load_user_edges()
        _init_analysis_cache()

        return {'status': 'created', 'filepath': filepath}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
