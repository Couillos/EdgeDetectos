"""
Unit tests for the Edge Generator backend API.
Run with: pytest webapp/tests/test_server.py -v
"""
import sys, os, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from fastapi.testclient import TestClient
from webapp.server import app, PROJECT_ROOT


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:
        yield c


def _check_edge_data(edge):
    """Verify an edge dict has all required fields."""
    assert isinstance(edge, dict)
    assert 'name' in edge and isinstance(edge['name'], str)
    assert 'has_analysis' in edge
    return edge


# ─── Root ─────────────────────────────────────────────────────────────

class TestRoot:
    def test_index_html(self, client):
        r = client.get('/')
        assert r.status_code == 200
        assert 'text/html' in r.headers['content-type']
        assert '<!DOCTYPE html>' in r.text

    def test_static_css(self, client):
        r = client.get('/static/app.css')
        assert r.status_code == 200
        assert 'text/css' in r.headers['content-type']

    def test_static_js(self, client):
        r = client.get('/static/app.js')
        assert r.status_code == 200
        assert 'javascript' in r.headers['content-type'] or 'text/plain' in r.headers['content-type']


# ─── Symbols ──────────────────────────────────────────────────────────

class TestSymbols:
    def test_list_symbols(self, client):
        r = client.get('/api/symbols')
        assert r.status_code == 200
        syms = r.json()
        assert isinstance(syms, list)
        assert len(syms) >= 1
        assert 'BTC/USDT' in syms


# ─── Edges ────────────────────────────────────────────────────────────

class TestEdges:
    def test_list_all(self, client):
        r = client.get('/api/edges')
        assert r.status_code == 200
        data = r.json()
        assert 'total' in data
        assert data['total'] > 1000
        assert 'edges' in data
        assert len(data['edges']) <= data['total']

    def test_pagination(self, client):
        r = client.get('/api/edges?per_page=10&page=1')
        assert r.status_code == 200
        data = r.json()
        assert len(data['edges']) <= 10
        assert data['page'] == 1
        assert data['per_page'] == 10

    def test_search(self, client):
        r = client.get('/api/edges?search=RSI&per_page=5')
        assert r.status_code == 200
        data = r.json()
        for e in data['edges']:
            assert 'RSI' in e['name']

    def test_sort_by_sharpe(self, client):
        r = client.get('/api/edges?sort=sharpe&order=desc&per_page=10')
        assert r.status_code == 200
        data = r.json()
        edges = data['edges']
        for i in range(1, len(edges)):
            e1 = edges[i - 1].get('best_sharpe', 0) or 0
            e2 = edges[i].get('best_sharpe', 0) or 0
            assert e1 >= e2 - 0.001

    def test_filter_status(self, client):
        r = client.get('/api/edges?status=analyzed')
        assert r.status_code == 200
        data = r.json()
        for e in data['edges']:
            assert e.get('has_analysis') is True

    def test_filter_status_pending(self, client):
        r = client.get('/api/edges?status=pending')
        assert r.status_code == 200
        data = r.json()
        for e in data['edges']:
            assert e.get('has_analysis') is False

    def test_edge_detail(self, client):
        name = 'ADX Positive DI Cross'
        import urllib.parse
        encoded = urllib.parse.quote(name, safe='')
        r = client.get(f'/api/edges/{encoded}')
        assert r.status_code == 200, f'Expected 200, got {r.status_code} for {name}'
        d = r.json()
        assert d.get('signal_name') == name, f"Expected '{name}', got '{d.get('signal_name')}'"
        assert 'horizons' in d
        assert 'verdict' in d
        assert 'report_png' in d
        assert d.get('best_mc_p') is not None

    def test_edge_detail_not_found(self, client):
        r = client.get('/api/edges/nonexistent_edge_xyz')
        assert r.status_code == 404

    def test_edge_detail_has_technical_scores(self, client):
        import urllib.parse
        encoded = urllib.parse.quote('ADX Positive DI Cross', safe='')
        r = client.get(f'/api/edges/{encoded}')
        d = r.json()
        for h_name, h_data in d.get('horizons', {}).items():
            assert 'mc_p' in h_data, f'mc_p missing in horizon {h_name}'
            assert 't_p' in h_data, f't_p missing in horizon {h_name}'
            assert 'ks_p' in h_data, f'ks_p missing in horizon {h_name}'

    def test_edge_detail_analyzed(self, client):
        import urllib.parse
        encoded = urllib.parse.quote('ADX Positive DI Cross', safe='')
        r = client.get(f'/api/edges/{encoded}')
        assert r.status_code == 200
        d = r.json()
        assert d.get('has_analysis') == True
        assert d.get('report_png') is not None

    def test_edge_detail_report_png(self, client):
        import urllib.parse
        encoded = urllib.parse.quote('ADX Positive DI Cross', safe='')
        r = client.get(f'/api/edges/{encoded}')
        assert r.status_code == 200
        d = r.json()
        assert 'report_png' in d
        assert d['report_png'] is None or d['report_png'].startswith('/api/report/')

    def test_edge_list_empty_search(self, client):
        r = client.get('/api/edges?search=zzzNOEDGEzzz')
        assert r.status_code == 200
        d = r.json()
        assert d['total'] == 0
        assert d['edges'] == []

    def test_edge_list_sort_by_winrate(self, client):
        r = client.get('/api/edges?sort=winrate&order=desc&per_page=10')
        assert r.status_code == 200
        d = r.json()
        if len(d['edges']) > 1:
            wr = [e.get('best_winrate') or 0 for e in d['edges']]
            assert wr == sorted(wr, reverse=True), 'desc winrate sort failed'

    def test_edge_list_combined_filters(self, client):
        r = client.get('/api/edges?search=24h&status=analyzed&sort=sharpe&order=desc')
        assert r.status_code == 200
        d = r.json()
        for e in d['edges']:
            assert '24h' in e['name']
            assert e['has_analysis'] == True

    def test_edge_list_different_symbol(self, client):
        r = client.get('/api/edges?symbol=DOGE%2FUSDT&per_page=5')
        assert r.status_code == 200


# ─── Indicators ───────────────────────────────────────────────────────

class TestIndicators:
    def test_list_indicators(self, client):
        r = client.get('/api/indicators')
        assert r.status_code == 200
        d = r.json()
        assert 'total' in d
        assert d['total'] >= 90  # we have 95 indicators
        assert 'categories' in d
        assert len(d['categories']) >= 5

    def test_category_structure(self, client):
        r = client.get('/api/indicators')
        d = r.json()
        for cat, indicators in d['categories'].items():
            assert isinstance(indicators, list)
            assert len(indicators) > 0
            assert isinstance(indicators[0], str)


# ─── Reports ──────────────────────────────────────────────────────────

class TestReports:
    def test_report_json(self, client):
        name = 'ulcer_stress_oversold'
        r = client.get(f'/api/report/{name}/json')
        assert r.status_code == 200
        assert 'application/json' in r.headers['content-type']
        d = r.json()
        assert 'signal_name' in d

    def test_report_png(self, client):
        name = 'ulcer_stress_oversold'
        r = client.get(f'/api/report/{name}/png')
        assert r.status_code == 200
        assert 'image/png' in r.headers['content-type']

    def test_report_not_found(self, client):
        r = client.get('/api/report/nonexistent/json')
        assert r.status_code == 404


# ─── Ranking ──────────────────────────────────────────────────────────

class TestRanking:
    def test_ranking_endpoint(self, client):
        r = client.get('/api/ranking?symbol=BTC/USDT')
        assert r.status_code == 200
        d = r.json()
        assert 'edges' in d
        assert len(d['edges']) > 0
        # First edge should have the highest score
        scores = [e['score'] for e in d['edges']]
        for i in range(1, len(scores)):
            assert scores[i - 1] >= scores[i]

    def test_ranking_has_technical_scores(self, client):
        r = client.get('/api/ranking?symbol=BTC/USDT')
        edges = r.json()['edges']
        e = edges[0]
        for field in ['t_p', 'mc_p', 'ks_p']:
            assert field in e, f'{field} missing in ranking edge'
            assert e[field] is not None

    def test_ranking_has_all_fields(self, client):
        r = client.get('/api/ranking?symbol=BTC/USDT')
        edges = r.json()['edges']
        required = ['name', 'score', 'sig', 'breadth', 'verdict', 'sharpe', 'winrate', 'total_return', 't_p', 'mc_p', 'ks_p']
        for field in required:
            assert field in edges[0], f'{field} missing in ranking edge'

    def test_ranking_png(self, client):
        r = client.get('/api/ranking/BTC_USDT/png')
        # May or may not exist
        assert r.status_code in (200, 404)

    def test_ranking_bad_symbol(self, client):
        r = client.get('/api/ranking?symbol=BAD/PAIR')
        assert r.status_code == 404

    def test_ranking_doge(self, client):
        r = client.get('/api/ranking?symbol=DOGE%2FUSDT')
        assert r.status_code == 200


# ─── OOS ──────────────────────────────────────────────────────────────

class TestOOS:
    def test_oos_endpoint(self, client):
        r = client.get('/api/oos/BTC_USDT')
        assert r.status_code == 200
        d = r.json()
        assert 'verdicts' in d
        assert 'edges' in d
        assert len(d['edges']) > 0

    def test_oos_verdicts(self, client):
        r = client.get('/api/oos/BTC_USDT')
        d = r.json()
        for v in ['STRONG', 'PASS', 'WEAK', 'FAIL']:
            assert v in d['verdicts']

    def test_oos_has_technical_scores(self, client):
        r = client.get('/api/oos/BTC_USDT')
        edges = r.json()['edges']
        e = edges[0]
        for field in ['oos_t_p', 'oos_mc_p', 'dist_ks_p']:
            assert field in e, f'{field} missing in OOS edge'

    def test_oos_has_all_fields(self, client):
        r = client.get('/api/oos/BTC_USDT')
        edges = r.json()['edges']
        required = ['name', 'verdict', 'is_score', 'oos_score', 'final_score', 'decay',
                     'oos_sharpe', 'oos_winrate', 'oos_t_p', 'oos_mc_p', 'dist_ks_p', 'is_sharpe']
        for field in required:
            assert field in edges[0], f'{field} missing in OOS edge'


    def test_oos_doge_symbol(self, client):
        r = client.get('/api/oos/DOGE_USDT')
        # May not exist if OOS not generated
        assert r.status_code in (200, 404)

    def test_oos_bad_symbol(self, client):
        r = client.get('/api/oos/BAD_PAIR')
        assert r.status_code == 404

    def test_oos_txt_summary(self, client):
        r = client.get('/api/oos/BTC_USDT')
        if r.status_code == 200:
            d = r.json()
            assert 'txt_summary' in d


# ─── Create Edge ──────────────────────────────────────────────────────

class TestCreateEdge:
    def test_create_edge_valid(self, client):
        r = client.post('/api/edges/create', json={
            'name': 'Test Unit Edge',
            'long_formula': 'close > sma(close, 20)',
            'horizons': '1,4,6',
            'description': 'Test edge from unit test'
        })
        assert r.status_code == 200
        d = r.json()
        assert d['status'] == 'created'

        # Cleanup
        fpath = os.path.join(PROJECT_ROOT, 'edges', 'test_unit_edge.py')
        if os.path.exists(fpath):
            os.remove(fpath)

    def test_create_edge_missing_name(self, client):
        r = client.post('/api/edges/create', json={
            'long_formula': 'close > open',
            'horizons': '1,4,6'
        })
        assert r.status_code == 422

    def test_create_edge_invalid_formula(self, client):
        r = client.post('/api/edges/create', json={
            'name': 'Bad Formula Edge',
            'long_formula': 'nonexistent_indicator(close)',
            'horizons': '1,4,6'
        })
        assert r.status_code == 200
        d = r.json()
        assert d['status'] == 'error'

    def test_create_edge_no_formula(self, client):
        r = client.post('/api/edges/create', json={
            'name': 'No Formula Edge',
            'horizons': '1,4,6'
        })
        assert r.status_code == 422
