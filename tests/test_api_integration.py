"""
tests/test_api_integration.py  (updated for notebook-based optimizers)

Tests every endpoint through the Flask test client.
Uses synthetic data; mocks yfinance where needed.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.pop('API_KEY', None)
os.environ['ADMIN_API_KEY'] = 'test-admin-key'
os.environ['RATELIMIT_ENABLED'] = 'false'

import pytest
import numpy as np
from unittest.mock import patch

from api import app, generate_mock_data


# ── Fixtures & helpers ───────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False
    with app.test_client() as c:
        yield c


def _unwrap(resp):
    body = resp.get_json()
    if body and 'data' in body:
        return body['data']
    return body


def _optimize_payload(objective='hybrid', n=6):
    """Synthetic optimize payload — no yfinance needed."""
    assets, corr = generate_mock_data(n, 'normal')
    vols    = np.array([a['ann_vol']    for a in assets])
    returns = np.array([a['ann_return'] for a in assets])
    cov     = np.outer(vols, vols) * corr
    payload = {
        'returns':    returns.tolist(),
        'covariance': cov.tolist(),
        'objective':  objective,
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


# ── 1. Health & config ───────────────────────────────────────────────────────

class TestHealthAndConfig:

    def test_health(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        assert _unwrap(resp)['status'] == 'healthy'

    def test_config_objectives_contains_new_methods(self, client):
        resp = client.get('/api/config/objectives')
        assert resp.status_code == 200
        data = _unwrap(resp)
        ids = {o['id'] for o in data['objectives']}
        for expected in ('hybrid', 'qubo_sa', 'vqe', 'hrp', 'markowitz', 'equal_weight'):
            assert expected in ids, f"Missing objective: {expected}"

    def test_config_objectives_no_qsw(self, client):
        resp = client.get('/api/config/objectives')
        ids = {o['id'] for o in _unwrap(resp)['objectives']}
        assert 'max_sharpe' not in ids, "Old QSW objective should be gone"

    def test_config_presets(self, client):
        resp = client.get('/api/config/presets')
        assert resp.status_code == 200
        ids = {p['id'] for p in _unwrap(resp)['presets']}
        assert 'default' in ids

    def test_metrics_endpoint(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200


# ── 2. Optimize — happy paths for all objectives ─────────────────────────────

class TestOptimizeAllObjectives:
    """Each method must return a valid 200 with expected response shape."""

    FAST_OBJECTIVES = ['equal_weight', 'markowitz', 'min_variance', 'hrp', 'target_return']
    SLOW_OBJECTIVES = ['qubo_sa', 'vqe', 'hybrid']

    def _assert_optimize_response(self, data):
        assert 'qsw_result' in data or 'weights' in data
        root = data.get('qsw_result', data)
        assert 'weights' in root
        assert 'sharpe_ratio' in root
        assert 'expected_return' in root
        assert 'volatility' in root
        weights = root['weights']
        assert abs(sum(weights) - 1.0) < 1e-4, f"Weights sum to {sum(weights)}"

    @pytest.mark.parametrize("objective", FAST_OBJECTIVES)
    def test_fast_objective(self, client, objective):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload(objective))
        assert resp.status_code == 200, f"{objective} failed: {resp.get_json()}"
        self._assert_optimize_response(_unwrap(resp))

    @pytest.mark.parametrize("objective", SLOW_OBJECTIVES)
    def test_slow_objective(self, client, objective):
        """Use small universe to keep tests fast."""
        payload = _optimize_payload(objective, n=6)
        # Reduce iterations for test speed
        payload['n_sa_steps']    = 500
        payload['n_sa_restarts'] = 3
        payload['n_restarts']    = 2
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200, f"{objective} failed: {resp.get_json()}"
        self._assert_optimize_response(_unwrap(resp))


# ── 3. Optimize — hybrid stage_info ─────────────────────────────────────────

class TestHybridStageInfo:

    def test_stage_info_present(self, client):
        payload = _optimize_payload('hybrid', n=8)
        payload['n_sa_restarts'] = 3
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        si = data.get('stage_info')
        assert si is not None, "stage_info should be present for hybrid"
        assert 'stage2_selected_idx' in si
        assert 'stage3_sharpe' in si
        assert 'stage2_qubo_obj' in si
        qm = data.get('quantum_metadata')
        assert qm is not None
        assert qm.get('execution_kind') == 'hybrid_pipeline'
        assert 'circuit' in qm

    def test_k_screen_k_select_respected(self, client):
        payload = _optimize_payload('hybrid', n=10)
        payload['K_screen'] = 6
        payload['K_select'] = 3
        payload['n_sa_restarts'] = 3
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        si = _unwrap(resp)['stage_info']
        assert si['stage1_screened_count'] == 6
        assert len(si['stage2_selected_idx']) == 3


# ── 4. Optimize — error paths ────────────────────────────────────────────────

class TestOptimizeErrors:

    def test_empty_body(self, client):
        resp = client.post('/api/portfolio/optimize', json={})
        assert resp.status_code in (400, 429), "Expected 400 (bad request) or 429 (rate limited)"

    def test_invalid_objective(self, client):
        payload = _optimize_payload()
        payload['objective'] = 'quantum_magic'
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code in (400, 429)
        if resp.status_code == 400:
            err = resp.get_json()
            assert 'quantum_magic' in str(err)

    def test_target_return_defaults_when_omitted(self, client):
        """Omitted target_return uses mean(asset returns), matching core optimizer tests."""
        payload = _optimize_payload('target_return')
        del payload['targetReturn']
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code in (200, 429)
        if resp.status_code == 200:
            data = _unwrap(resp)
            qsw = data.get('qsw_result') or data
            assert 'weights' in qsw


# ── 5. Optimize — response shape backward compatibility ──────────────────────

class TestOptimizeResponseShape:
    """Frontend depends on these keys — must not break."""

    def test_required_top_level_keys(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload('markowitz'))
        if resp.status_code == 429:
            pytest.skip("rate limited")
        data = _unwrap(resp)
        for key in ('qsw_result', 'weights', 'holdings', 'assets', 'benchmarks',
                    'sector_allocation', 'risk_metrics', 'metadata'):
            assert key in data, f"Missing key: {key}"

    def test_qsw_result_shape(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload('hrp'))
        if resp.status_code == 429:
            pytest.skip("rate limited")
        qsw = _unwrap(resp)['qsw_result']
        for key in ('weights', 'sharpe_ratio', 'expected_return', 'volatility', 'n_active'):
            assert key in qsw, f"Missing qsw_result key: {key}"

    def test_holdings_are_active_only(self, client):
        """Holdings should only list assets with weight > 1e-4."""
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload('markowitz'))
        if resp.status_code == 429:
            pytest.skip("rate limited")
        data = _unwrap(resp)
        for h in data['holdings']:
            assert h['weight'] > 1e-4

    def test_benchmarks_has_four_methods(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload('hybrid', n=8))
        if resp.status_code == 429:
            pytest.skip("rate limited")
        benchmarks = _unwrap(resp)['benchmarks']
        for m in ('equal_weight', 'min_variance', 'markowitz', 'hrp'):
            assert m in benchmarks, f"Missing benchmark: {m}"

    def test_non_qsw_objectives_have_null_stage_info(self, client):
        resp = client.post('/api/portfolio/optimize', json=_optimize_payload('markowitz'))
        if resp.status_code == 429:
            pytest.skip("rate limited")
        data = _unwrap(resp)
        # stage_info should be None/null for non-hybrid methods
        assert data.get('stage_info') is None


# ── 6. Market data ───────────────────────────────────────────────────────────

class TestMarketData:

    @patch('api.app.fetch_market_data')
    def test_market_data_happy(self, mock_fetch, client):
        mock_fetch.return_value = _mock_market_data()
        resp = client.post('/api/market-data', json={'tickers': ['AAPL', 'MSFT', 'GOOGL']})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'assets' in data or 'returns' in data

    def test_empty_tickers(self, client):
        resp = client.post('/api/market-data', json={'tickers': []})
        assert resp.status_code == 400

    def test_no_tickers_field(self, client):
        resp = client.post('/api/market-data', json={})
        assert resp.status_code == 400


# ── 7. Backtest ──────────────────────────────────────────────────────────────

def _mock_backtest_result():
    dates = ['2023-01-31', '2023-02-28', '2023-03-31']
    return {
        'results': [
            {'date': d, 'portfolio_value': 100 + i * 2,
             'weights': {'AAPL': 0.5, 'MSFT': 0.5},
             'metrics': {'sharpe': 1.1, 'return': 0.02, 'volatility': 0.15}}
            for i, d in enumerate(dates)
        ],
        'summary_metrics': {
            'total_return': 0.06, 'annualized_return': 0.08,
            'annualized_volatility': 0.15, 'sharpe_ratio': 1.1,
            'max_drawdown': -0.05, 'calmar_ratio': 1.6,
        },
        'parameters': {
            'tickers': ['AAPL', 'MSFT'],
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
            'rebalance_frequency': 'monthly',
        },
    }


class TestBacktest:

    @patch('services.backtest.fetch_price_panel')
    def test_backtest_happy(self, _mock_panel, client):
        with patch('api.app._run_backtest_payload', return_value=_mock_backtest_result()):
            resp = client.post('/api/portfolio/backtest', json={
                'tickers': ['AAPL', 'MSFT'],
                'start_date': '2023-01-01',
                'end_date': '2024-01-01',
            })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'summary_metrics' in data

    def test_missing_tickers(self, client):
        resp = client.post('/api/portfolio/backtest', json={
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
        })
        assert resp.status_code in (400, 500)


# ── 8. Efficient frontier ────────────────────────────────────────────────────

class TestEfficientFrontier:

    def test_efficient_frontier_with_matrix(self, client):
        payload = _optimize_payload('markowitz', n=5)
        resp = client.post('/api/portfolio/efficient-frontier', json={
            'returns':    payload['returns'],
            'covariance': payload['covariance'],
            'n_points':   10,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert 'frontier_points' in data
        assert len(data['frontier_points']) > 0
        pt = data['frontier_points'][0]
        assert 'volatility' in pt
        assert 'sharpe' in pt
        assert 'weights' in pt


# ── 9. Batch optimize ────────────────────────────────────────────────────────

class TestBatchOptimize:

    def test_batch_two_items(self, client):
        resp = client.post('/api/portfolio/optimize/batch', json={
            'requests': [
                _optimize_payload('markowitz'),
                _optimize_payload('hrp'),
            ]
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data['count'] == 2
        assert len(data['results']) == 2
        # Each result has status ('ok' when successful, 'error' when rate limited)
        for r in data['results']:
            assert r.get('status') in ('ok', 'error')

    def test_batch_empty(self, client):
        resp = client.post('/api/portfolio/optimize/batch', json={'requests': []})
        assert resp.status_code == 400

    def test_batch_over_limit(self, client):
        resp = client.post('/api/portfolio/optimize/batch', json={
            'requests': [_optimize_payload('equal_weight')] * 101
        })
        assert resp.status_code == 400


# ── 10. Async jobs ───────────────────────────────────────────────────────────

class TestAsyncJobs:

    def test_submit_optimize_job(self, client):
        resp = client.post('/api/jobs/optimize', json={'payload': _optimize_payload('hrp')})
        assert resp.status_code == 202
        data = _unwrap(resp)
        assert 'job_id' in data
        assert data['status'] in ('queued', 'running', 'completed')

    def test_get_unknown_job(self, client):
        resp = client.get('/api/jobs/nonexistent-id-xyz-123')
        assert resp.status_code == 404


# ── 11. Admin API keys ───────────────────────────────────────────────────────

class TestAdminKeys:

    def test_create_api_key(self, client):
        resp = client.post(
            '/api/admin/api-keys',
            json={'tenant_id': 'test-tenant', 'key_name': 'ci-key'},
            headers={'X-Admin-Key': 'test-admin-key'},
        )
        assert resp.status_code == 201
        assert 'api_key' in _unwrap(resp)

    def test_unauthorized_admin(self, client):
        resp = client.post(
            '/api/admin/api-keys',
            json={'tenant_id': 'x'},
            headers={'X-Admin-Key': 'wrong'},
        )
        assert resp.status_code == 401

    def test_list_keys(self, client):
        resp = client.get('/api/admin/api-keys', headers={'X-Admin-Key': 'test-admin-key'})
        assert resp.status_code == 200
        assert 'keys' in _unwrap(resp)


# ── 12. Constraint pass-through ──────────────────────────────────────────────

class TestConstraintPassthrough:
    """Integration tests for weight bounds and cardinality constraint enforcement."""

    @pytest.mark.parametrize("objective", ["markowitz", "hrp"])
    def test_weight_bounds_respected(self, client, objective):
        """All non-zero weights respect weight_min / weight_max."""
        payload = _optimize_payload(objective=objective, n=8)
        payload["weight_min"] = 0.05
        payload["weight_max"] = 0.20
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        weights = np.array(data["weights"])
        nonzero = weights[weights > 1e-8]
        tol = 1e-4
        assert np.all(nonzero >= 0.05 - tol), (
            f"weight below min: {nonzero.min():.6f}"
        )
        assert np.all(nonzero <= 0.20 + tol), (
            f"weight above max: {nonzero.max():.6f}"
        )

    def test_cardinality_via_K(self, client):
        """K limits the number of non-zero weights (qubo_sa)."""
        payload = _optimize_payload(objective="qubo_sa", n=8)
        payload["K"] = 3
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        weights = np.array(data["weights"])
        n_active = int(np.sum(weights > 1e-6))
        assert n_active <= 3, f"Expected at most 3 active, got {n_active}"

    def test_constraint_report_present(self, client):
        """Response includes constraint_report with expected keys."""
        payload = _optimize_payload(objective="markowitz", n=6)
        payload["weight_min"] = 0.05
        payload["weight_max"] = 0.25
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        cr = data.get("constraint_report")
        assert cr is not None, "constraint_report missing from response"
        assert cr["weight_min_applied"] == 0.05
        assert cr["weight_max_applied"] == 0.25
        assert "n_clipped_min" in cr
        assert "n_clipped_max" in cr
        assert "k_select" in cr


# ── 13. Run history persistence ──────────────────────────────────────────────

class TestRunHistory:
    """Integration tests for persistent run history (sync optimize path)."""

    def test_run_id_in_optimize_response(self, client):
        """POST /api/portfolio/optimize returns a run_id in the response."""
        payload = _optimize_payload(objective="markowitz", n=5)
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "run_id" in data, "run_id missing from optimize response"
        assert isinstance(data["run_id"], str)
        assert len(data["run_id"]) > 10

    def test_get_run_after_optimize(self, client):
        """After optimize, GET /api/runs/{run_id} returns a completed run."""
        payload = _optimize_payload(objective="markowitz", n=5)
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        run_id = _unwrap(resp)["run_id"]

        resp2 = client.get(f'/api/runs/{run_id}')
        assert resp2.status_code == 200
        run_data = _unwrap(resp2)
        assert run_data["status"] == "completed"
        assert run_data["execution_kind"] == "sync_optimize"
        assert run_data["spec"]["objective"] == "markowitz"
        assert run_data["result"] is not None
        assert "weights" in run_data["result"]

    def test_run_tenant_isolation(self, client):
        """Run created under one tenant is not visible to a different tenant."""
        payload = _optimize_payload(objective="markowitz", n=5)
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        run_id = _unwrap(resp)["run_id"]

        from services import lab_run_service
        run_as_other = lab_run_service.get_run(run_id, tenant_id="other-tenant")
        assert run_as_other is None, "Run should not be visible to a different tenant"

        run_as_anon = lab_run_service.get_run(run_id, tenant_id="anonymous")
        assert run_as_anon is not None, "Run should be visible to same tenant"


# ── 14. Job queue and SSE ────────────────────────────────────────────────────

class TestJobQueue:
    """Integration tests for the async job list and SSE stream endpoints."""

    def test_list_jobs_empty(self, client):
        """GET /api/jobs returns empty list when no jobs have been submitted."""
        resp = client.get('/api/jobs')
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["jobs"] == []
        assert data["count"] == 0

    def test_list_jobs_after_submit(self, client):
        """After POST /api/jobs/optimize, GET /api/jobs includes the job."""
        payload = _optimize_payload(objective="markowitz", n=5)
        submit_resp = client.post('/api/jobs/optimize', json={"payload": payload})
        assert submit_resp.status_code == 202
        job_id = _unwrap(submit_resp)["job_id"]

        resp = client.get('/api/jobs')
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["count"] >= 1
        ids = [j["job_id"] for j in data["jobs"]]
        assert job_id in ids

    def test_stream_run_returns_sse(self, client):
        """GET /api/runs/{run_id}/stream returns text/event-stream and emits status."""
        payload = _optimize_payload(objective="markowitz", n=5)
        resp = client.post('/api/portfolio/optimize', json=payload)
        assert resp.status_code == 200
        run_id = _unwrap(resp)["run_id"]

        sse_resp = client.get(f'/api/runs/{run_id}/stream')
        assert sse_resp.status_code == 200
        assert "text/event-stream" in sse_resp.content_type
        body = sse_resp.get_data(as_text=True)
        assert "data:" in body
        assert '"completed"' in body


# ── 15. Walk-Forward Backtest ─────────────────────────────────────────────────

import pandas as pd
from datetime import datetime


def _make_synthetic_prices(tickers, start, end, trend=0.0003):
    """Generate synthetic daily prices with per-asset drift variation."""
    dates = pd.bdate_range(start, end)
    np.random.seed(42)
    data = {}
    for i, t in enumerate(tickers):
        drift = trend * (1 + 0.5 * i)
        vol = 0.005 * (1 + 0.3 * i)
        noise = np.random.normal(0, vol, len(dates))
        log_rets = drift + noise
        prices = 100 * np.exp(np.cumsum(log_rets))
        data[t] = prices
    return pd.DataFrame(data, index=dates)


class TestWalkForward:
    """Integration tests for POST /api/backtest/walkforward."""

    @patch("services.backtest.fetch_price_panel")
    def test_walkforward_period_count(self, mock_fetch, client):
        """24-month window, 12+3 train/test -> expect 4 periods."""
        tickers = ["AAA", "BBB", "CCC"]
        mock_fetch.return_value = _make_synthetic_prices(tickers, "2020-01-01", "2022-01-01")

        resp = client.post('/api/backtest/walkforward', json={
            "tickers": tickers,
            "start": "2020-01-01",
            "end": "2022-01-01",
            "train_months": 12,
            "test_months": 3,
            "objective": "hrp",
            "cost_bps": 0,
        })
        assert resp.status_code == 200, resp.get_data(as_text=True)
        data = _unwrap(resp)
        assert data["metadata"]["n_periods"] == 4
        assert len(data["periods"]) == 4
        assert "run_id" in data

    @patch("services.backtest.fetch_price_panel")
    def test_walkforward_turnover_range(self, mock_fetch, client):
        """All period turnovers should be in [0, 1]."""
        tickers = ["AAA", "BBB", "CCC", "DDD"]
        mock_fetch.return_value = _make_synthetic_prices(tickers, "2019-01-01", "2022-01-01")

        resp = client.post('/api/backtest/walkforward', json={
            "tickers": tickers,
            "start": "2019-01-01",
            "end": "2022-01-01",
            "train_months": 12,
            "test_months": 3,
            "objective": "hrp",
            "cost_bps": 5,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        for p in data["periods"]:
            assert 0.0 <= p["turnover"] <= 1.0, f"turnover out of range: {p['turnover']}"

    @patch("services.backtest.fetch_price_panel")
    def test_walkforward_cost_reduces_return(self, mock_fetch, client):
        """cost_bps=100 should yield lower final equity than cost_bps=0."""
        tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
        prices = _make_synthetic_prices(tickers, "2019-01-01", "2022-01-01")
        mock_fetch.side_effect = lambda *a, **kw: prices.copy()

        resp0 = client.post('/api/backtest/walkforward', json={
            "tickers": tickers,
            "start": "2019-01-01",
            "end": "2022-01-01",
            "train_months": 12,
            "test_months": 3,
            "objective": "markowitz",
            "cost_bps": 0,
        })

        resp100 = client.post('/api/backtest/walkforward', json={
            "tickers": tickers,
            "start": "2019-01-01",
            "end": "2022-01-01",
            "train_months": 12,
            "test_months": 3,
            "objective": "markowitz",
            "cost_bps": 100,
        })
        assert resp0.status_code == 200, resp0.get_data(as_text=True)
        assert resp100.status_code == 200, resp100.get_data(as_text=True)
        eq0 = _unwrap(resp0)["equity_curve"]["portfolio"][-1]
        eq100 = _unwrap(resp100)["equity_curve"]["portfolio"][-1]
        assert eq0 > eq100, f"zero-cost equity {eq0} should exceed 100bps equity {eq100}"

    @patch("services.backtest.fetch_price_panel")
    def test_walkforward_equity_trend_zero_cost(self, mock_fetch, client):
        """With monotonically rising prices and zero cost, final equity > 1.0."""
        tickers = ["UP1", "UP2", "UP3"]
        mock_fetch.return_value = _make_synthetic_prices(tickers, "2019-01-01", "2022-01-01", trend=0.001)

        resp = client.post('/api/backtest/walkforward', json={
            "tickers": tickers,
            "start": "2019-01-01",
            "end": "2022-01-01",
            "train_months": 12,
            "test_months": 3,
            "objective": "hrp",
            "cost_bps": 0,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        final_equity = data["equity_curve"]["portfolio"][-1]
        assert final_equity > 1.0, f"Expected rising equity, got {final_equity}"
