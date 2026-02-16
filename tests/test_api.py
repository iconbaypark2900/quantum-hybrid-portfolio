"""
Tests for the Quantum Hybrid Portfolio API endpoints.
Uses Flask test client. Mocks external calls (yfinance) to avoid network dependencies.
API_KEY should be unset so auth is bypassed.
"""
import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Unset API_KEY before importing api so auth is bypassed
os.environ.pop('API_KEY', None)

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Import app and generate_mock_data after path and env are set
from api import app, generate_mock_data


# ─── Fixtures ───

@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False  # Disable rate limiting in tests
    with app.test_client() as c:
        yield c


def _minimal_optimize_payload():
    """Minimal valid payload for POST /api/portfolio/optimize using returns/covariance."""
    n_assets = 5
    assets, corr = generate_mock_data(n_assets, 'normal')
    vols = np.array([a['ann_vol'] for a in assets])
    returns = np.array([a['ann_return'] for a in assets])
    covariance = np.outer(vols, vols) * corr
    return {
        'returns': returns.tolist(),
        'covariance': covariance.tolist(),
    }


def _mock_market_data_response(tickers=None):
    """Return mock market data in the format expected by the API."""
    tickers = tickers or ['AAPL', 'MSFT', 'GOOGL']
    n = len(tickers)
    returns = [0.08 + i * 0.02 for i in range(n)]
    cov = np.eye(n) * 0.04 + np.ones((n, n)) * 0.01
    return {
        'assets': tickers,
        'names': [f'Company {t}' for t in tickers],
        'sectors': ['Technology'] * n,
        'returns': returns,
        'covariance': cov.tolist(),
        'start_date': '2023-01-01',
        'end_date': '2024-01-01',
        'data_points': 252,
        'success': True,
        'message': f'Successfully fetched data for {n} assets',
    }


# ─── Tests ───

def test_health_returns_200_and_json(client):
    """Test GET /api/health returns 200 and correct JSON."""
    resp = client.get('/api/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data.get('status') == 'healthy'
    assert 'message' in data
    assert 'Quantum' in data.get('message', '')


def test_config_objectives_returns_200(client):
    """Test GET /api/config/objectives returns 200."""
    resp = client.get('/api/config/objectives')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'objectives' in data
    assert len(data['objectives']) > 0
    assert any(obj.get('id') == 'max_sharpe' for obj in data['objectives'])


def test_config_presets_returns_200(client):
    """Test GET /api/config/presets returns 200."""
    resp = client.get('/api/config/presets')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'presets' in data
    assert len(data['presets']) > 0
    assert any(p.get('id') == 'balanced' for p in data['presets'])


def test_config_constraints_returns_200(client):
    """Test GET /api/config/constraints returns 200."""
    resp = client.get('/api/config/constraints')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'sector_limits' in data or 'cardinality' in data


@patch('api.fetch_market_data')
def test_portfolio_optimize_with_minimal_valid_data(mock_fetch, client):
    """Test POST /api/portfolio/optimize with minimal valid data via generate_mock_data."""
    payload = _minimal_optimize_payload()
    resp = client.post(
        '/api/portfolio/optimize',
        json=payload,
        content_type='application/json',
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'qsw_result' in data
    assert 'holdings' in data
    assert 'benchmarks' in data
    assert 'weights' in data['qsw_result']
    mock_fetch.assert_not_called()  # Uses returns/covariance path, no yfinance


def test_portfolio_optimize_missing_data_returns_400(client):
    """Test POST /api/portfolio/optimize with missing data returns 400."""
    resp = client.post(
        '/api/portfolio/optimize',
        json={},
        content_type='application/json',
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data is not None
    assert 'error' in data

    # Also test with neither tickers nor returns/covariance
    resp2 = client.post(
        '/api/portfolio/optimize',
        json={'regime': 'normal'},
        content_type='application/json',
    )
    assert resp2.status_code == 400


def test_market_data_empty_tickers_returns_400(client):
    """Test POST /api/market-data with invalid/empty tickers returns 400."""
    resp = client.post(
        '/api/market-data',
        json={'tickers': []},
        content_type='application/json',
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'error' in data

    # Empty list
    resp2 = client.post(
        '/api/market-data',
        json={},
        content_type='application/json',
    )
    assert resp2.status_code == 400


def test_backtest_missing_required_fields_returns_400(client):
    """Test POST /api/portfolio/backtest with missing required fields returns 400."""
    # Missing tickers
    resp = client.post(
        '/api/portfolio/backtest',
        json={'start_date': '2023-01-01', 'end_date': '2024-01-01'},
        content_type='application/json',
    )
    assert resp.status_code == 400

    # Missing dates
    resp2 = client.post(
        '/api/portfolio/backtest',
        json={'tickers': ['AAPL', 'MSFT']},
        content_type='application/json',
    )
    assert resp2.status_code == 400

    # Invalid date order
    resp3 = client.post(
        '/api/portfolio/backtest',
        json={
            'tickers': ['AAPL', 'MSFT'],
            'start_date': '2024-01-01',
            'end_date': '2023-01-01',
        },
        content_type='application/json',
    )
    assert resp3.status_code == 400


@patch('api.fetch_market_data')
def test_efficient_frontier_with_minimal_valid_data(mock_fetch, client):
    """Test POST /api/portfolio/efficient-frontier with minimal valid data."""
    mock_fetch.return_value = _mock_market_data_response(['AAPL', 'MSFT', 'GOOGL'])

    resp = client.post(
        '/api/portfolio/efficient-frontier',
        json={
            'tickers': ['AAPL', 'MSFT', 'GOOGL'],
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
            'n_points': 5,
        },
        content_type='application/json',
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'frontier_points' in data
    assert 'min_return' in data
    assert 'max_return' in data
    assert 'tickers' in data
    mock_fetch.assert_called_once()
