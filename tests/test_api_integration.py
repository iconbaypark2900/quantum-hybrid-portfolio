"""
API integration tests — every endpoint through the Flask test client.

Tests both happy-path (200) and error-path (400/404) for all 16 endpoints.
Uses synthetic data; mocks yfinance where needed.

Note: All successful API responses use a standardized envelope:
  { "data": { ... }, "meta": { ... } }
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Bypass auth and set admin key for admin tests
os.environ.pop('API_KEY', None)
os.environ['ADMIN_API_KEY'] = 'test-admin-key'

import pytest
import numpy as np
from unittest.mock import patch

from api import app, generate_mock_data


# ─── Fixtures & helpers ───

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False
    with app.test_client() as c:
        yield c


def _unwrap(resp):
    """Unwrap the standardized API envelope { data: ..., meta: ... }."""
    body = resp.get_json()
    if body and 'data' in body:
        return body['data']
    return body


def _optimize_payload(objective='max_sharpe', n=5):
    assets, corr = generate_mock_data(n, 'normal')
    vols = np.array([a['ann_vol'] for a in assets])
    returns = np.array([a['ann_return'] for a in assets])
    cov = np.outer(vols, vols) * corr
    payload = {
        'returns': returns.tolist(),
        'covariance': cov.tolist(),
        'objective': objective,
    }
    if objective == 'target_return':
        payload['targetReturn'] = float(np.mean(returns))
    return payload


def _mock_market_data(tickers=None):
    tickers = tickers or ['AAPL', 'MSFT', 'GOOGL']
    n = len(tickers)
    return {
        'assets': tickers,
        'names': [f'Company {t}' for t in tickers],
        'sectors': ['Technology'] * n,
        'returns': [0.08 + i * 0.02 for i in range(n)],
        'covariance': (np.eye(n) * 0.04 + np.ones((n, n)) * 0.01).tolist(),
        'start_date': '2023-01-01',
        'end_date': '2024-01-01',
        'data_points': 252,
        'success': True,
        'message': f'Fetched {n} assets',
    }


# ============================================================================
# 1. Config / health endpoints
# ============================================================================

class TestHealthAndConfig:

    def test_health(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data['status'] == 'healthy'

    def test_config_objectives_includes_hrp(self, client):
        resp = client.get('/api/config/objectives')
        assert resp.status_code == 200
        ids = [o['id'] for o in _unwrap(resp)['objectives']]
        assert 'hrp' in ids

    def test_config_presets(self, client):
        resp = client.get('/api/config/presets')
        assert resp.status_code == 200
        assert any(p['id'] == 'balanced' for p in _unwrap(resp)['presets'])

    def test_config_constraints(self, client):
        resp = client.get('/api/config/constraints')
        assert resp.status_code == 200

    def test_metrics_endpoint(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        assert resp.content_type.startswith('text/')


# ============================================================================
# 2. Portfolio optimize — happy paths for each objective
# ============================================================================

class TestOptimizeHappy:

    @pytest.mark.parametrize('objective', [
        'max_sharpe', 'min_variance', 'risk_parity', 'target_return', 'hrp',
    ])
    def test_optimize_returns_200(self, client, objective):
        payload = _optimize_payload(objective=objective)
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'qsw_result' in data
        assert 'holdings' in data
        assert 'benchmarks' in data

    def test_optimize_weights_sum_to_one(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload())
        weights = _unwrap(resp)['qsw_result']['weights']
        assert abs(sum(weights) - 1.0) < 1e-4

    def test_optimize_benchmarks_include_hrp(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload())
        benchmarks = _unwrap(resp)['benchmarks']
        assert 'hrp' in benchmarks
        assert 'equal_weight' in benchmarks

    def test_optimize_objective_echoed(self, client):
        payload = _optimize_payload(objective='hrp')
        resp = client.post('/api/portfolio/optimize', json=payload)
        if resp.status_code == 429:
            pytest.skip("rate limited")
        data = _unwrap(resp)
        assert data['objective'] == 'hrp'

    def test_optimize_metrics_finite(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload())
        if resp.status_code == 429:
            pytest.skip("rate limited")
        r = _unwrap(resp)['qsw_result']
        for key in ['sharpe_ratio', 'expected_return', 'volatility']:
            assert np.isfinite(r[key]), f"{key} is not finite"

    def test_optimize_braket_annealing_returns_backend_type(self, client):
        """Braket annealing objective returns backend_type (braket or classical_qubo)."""
        payload = _optimize_payload(objective='braket_annealing')
        resp = client.post('/api/portfolio/optimize', json=payload)
        if resp.status_code == 429:
            pytest.skip("rate limited")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'qsw_result' in data
        assert 'holdings' in data
        # Without real Braket device, backend_type should be classical_qubo
        assert data.get('backend_type') in ('braket', 'classical_qubo')
        weights = data['qsw_result']['weights']
        assert abs(sum(weights) - 1.0) < 1e-4


# ============================================================================
# 3. Portfolio optimize — error paths
# ============================================================================

class TestOptimizeErrors:

    def test_missing_body(self, client):
        resp = client.post('/api/portfolio/optimize', json={})
        assert resp.status_code in (400, 429)

    def test_no_json_body(self, client):
        resp = client.post('/api/portfolio/optimize', data=b'', content_type='application/json')
        assert resp.status_code in (400, 429)


# ============================================================================
# 4. Market data
# ============================================================================

class TestMarketData:

    @patch('api.fetch_market_data')
    def test_market_data_happy(self, mock_fetch, client):
        mock_fetch.return_value = _mock_market_data()
        resp = client.post('/api/market-data', json={'tickers': ['AAPL', 'MSFT', 'GOOGL']})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'assets' in data or 'returns' in data

    def test_market_data_empty_tickers(self, client):
        resp = client.post('/api/market-data', json={'tickers': []})
        assert resp.status_code == 400


# ============================================================================
# 5. Backtest
# ============================================================================

def _backtest_request_payload():
    """Return a minimal valid backtest request dict."""
    return {
        'tickers': ['AAPL', 'MSFT'],
        'start_date': '2023-01-01',
        'end_date': '2024-01-01',
    }


def _mock_backtest_result():
    """Return a mock backtest result matching the shape produced by services.backtest."""
    return {
        'summary_metrics': {
            'total_return': 0.10,
            'annual_return': 0.05,
            'sharpe_ratio': 0.80,
            'max_drawdown': -0.05,
            'volatility': 0.15,
        },
        'results': [
            {'date': '2023-06-01', 'cumulative_value': 100, 'portfolio_return': 0.0},
            {'date': '2024-01-01', 'cumulative_value': 110, 'portfolio_return': 0.10},
        ],
    }


class TestBacktest:

    def test_backtest_missing_fields(self, client):
        resp = client.post('/api/portfolio/backtest', json={'tickers': ['AAPL', 'MSFT']})
        assert resp.status_code == 400

    def test_backtest_invalid_dates(self, client):
        resp = client.post('/api/portfolio/backtest', json={
            'tickers': ['AAPL', 'MSFT'],
            'start_date': '2024-01-01',
            'end_date': '2023-01-01',
        })
        assert resp.status_code == 400

    @patch('api.run_backtesting')
    def test_backtest_happy_path(self, mock_bt, client):
        mock_bt.return_value = _mock_backtest_result()
        resp = client.post('/api/portfolio/backtest', json=_backtest_request_payload())
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'summary_metrics' in data
        assert 'results' in data
        assert data['summary_metrics']['sharpe_ratio'] == 0.80


# ============================================================================
# 5b. Batch backtest
# ============================================================================

class TestBatchBacktest:

    @patch('api.run_backtesting')
    def test_batch_backtest_two_requests(self, mock_bt, client):
        mock_bt.return_value = _mock_backtest_result()
        payload = {
            'requests': [_backtest_request_payload(), _backtest_request_payload()],
        }
        resp = client.post('/api/portfolio/backtest/batch', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data['count'] == 2
        assert len(data['results']) == 2
        for item in data['results']:
            assert item['status'] == 'ok'
            assert 'result' in item
            assert 'summary_metrics' in item['result']

    def test_batch_backtest_empty_requests(self, client):
        resp = client.post('/api/portfolio/backtest/batch', json={'requests': []})
        assert resp.status_code == 400

    @patch('api.run_backtesting')
    def test_batch_backtest_stop_on_error(self, mock_bt, client):
        mock_bt.return_value = _mock_backtest_result()
        payload = {
            'requests': [
                _backtest_request_payload(),
                {'tickers': ['AAPL'], 'start_date': '2024-01-01'},
            ],
            'stop_on_error': True,
        }
        resp = client.post('/api/portfolio/backtest/batch', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data['count'] == 2
        assert data['results'][0]['status'] == 'ok'
        assert data['results'][1]['status'] == 'error'


# ============================================================================
# 6. Efficient frontier
# ============================================================================

class TestEfficientFrontier:

    @patch('api.fetch_market_data')
    def test_frontier_happy(self, mock_fetch, client):
        mock_fetch.return_value = _mock_market_data()
        resp = client.post('/api/portfolio/efficient-frontier', json={
            'tickers': ['AAPL', 'MSFT', 'GOOGL'],
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
            'n_points': 5,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'frontier_points' in data

    def test_frontier_missing_tickers(self, client):
        resp = client.post('/api/portfolio/efficient-frontier', json={})
        assert resp.status_code == 400


# ============================================================================
# 7. Batch optimize
# ============================================================================

class TestBatchOptimize:

    def test_batch_two_items(self, client):
        payload = {
            'requests': [_optimize_payload(), _optimize_payload(objective='hrp')]
        }
        resp = client.post('/api/portfolio/optimize/batch', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data['count'] == 2

    def test_batch_empty(self, client):
        resp = client.post('/api/portfolio/optimize/batch', json={'requests': []})
        # Empty batch returns 200 with count=0 or 400
        assert resp.status_code in (200, 400)


# ============================================================================
# 8. Async jobs
# ============================================================================

class TestAsyncJobs:

    def test_submit_optimize_job(self, client):
        payload = _optimize_payload()
        resp = client.post('/api/jobs/optimize', json={'payload': payload})
        assert resp.status_code == 202
        data = _unwrap(resp)
        assert 'job_id' in data

    def test_submit_backtest_job(self, client):
        payload = {
            'tickers': ['AAPL', 'MSFT'],
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
        }
        resp = client.post('/api/jobs/backtest', json={'payload': payload})
        assert resp.status_code == 202
        data = _unwrap(resp)
        assert 'job_id' in data

    def test_get_unknown_job(self, client):
        resp = client.get('/api/jobs/nonexistent-id-12345')
        assert resp.status_code == 404


# ============================================================================
# 9. Admin API keys
# ============================================================================

class TestAdminKeys:

    @pytest.fixture(autouse=True)
    def _set_admin_key(self, monkeypatch):
        monkeypatch.setenv('ADMIN_API_KEY', 'test-admin-key')

    def test_create_api_key(self, client):
        resp = client.post(
            '/api/admin/api-keys',
            json={'tenant_id': 'test-tenant-integration', 'key_name': 'ci-key'},
            headers={'X-Admin-Key': 'test-admin-key'},
        )
        assert resp.status_code == 201
        data = _unwrap(resp)
        assert 'api_key' in data

    def test_create_api_key_unauthorized(self, client):
        resp = client.post(
            '/api/admin/api-keys',
            json={'tenant_id': 'test'},
            headers={'X-Admin-Key': 'wrong-key'},
        )
        assert resp.status_code == 401

    def test_list_api_keys(self, client):
        resp = client.get(
            '/api/admin/api-keys',
            headers={'X-Admin-Key': 'test-admin-key'},
        )
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'keys' in data
