"""
Golden-value tests for _portfolio_metrics.

These tests pin the exact formulae:
  r   = w @ mu
  vol = sqrt(w @ Sigma @ w)
  SR  = (r - rf) / vol   (rf defaults to 0)
  n_active = sum(w > 1e-4)

All inputs and expected outputs are computed analytically so any
regression in the formula is caught immediately.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.portfolio_optimizer import _portfolio_metrics


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_2asset():
    """2-asset universe with known closed-form metrics."""
    w = np.array([0.4, 0.6])
    mu = np.array([0.12, 0.08])           # 12%, 8% annual
    # Diagonal Sigma (uncorrelated): vol_1=0.2, vol_2=0.15
    Sigma = np.diag([0.04, 0.0225])       # 0.2^2, 0.15^2
    return w, mu, Sigma


# ── basic correctness ─────────────────────────────────────────────────────────

def test_expected_return(simple_2asset):
    w, mu, Sigma = simple_2asset
    out = _portfolio_metrics(w, mu, Sigma)
    expected = 0.4 * 0.12 + 0.6 * 0.08   # = 0.096
    assert out["return"] == pytest.approx(expected, rel=1e-10)


def test_volatility_uncorrelated(simple_2asset):
    w, mu, Sigma = simple_2asset
    out = _portfolio_metrics(w, mu, Sigma)
    # vol = sqrt(0.4^2*0.04 + 0.6^2*0.0225)
    expected_var = 0.4**2 * 0.04 + 0.6**2 * 0.0225
    assert out["volatility"] == pytest.approx(math.sqrt(expected_var), rel=1e-10)


def test_sharpe_rf_zero(simple_2asset):
    w, mu, Sigma = simple_2asset
    out = _portfolio_metrics(w, mu, Sigma)
    r = 0.4 * 0.12 + 0.6 * 0.08
    v = math.sqrt(0.4**2 * 0.04 + 0.6**2 * 0.0225)
    assert out["sharpe"] == pytest.approx(r / v, rel=1e-10)


def test_sharpe_with_rf(simple_2asset):
    w, mu, Sigma = simple_2asset
    rf = 0.04
    out = _portfolio_metrics(w, mu, Sigma, rf=rf)
    r = 0.4 * 0.12 + 0.6 * 0.08
    v = math.sqrt(0.4**2 * 0.04 + 0.6**2 * 0.0225)
    assert out["sharpe"] == pytest.approx((r - rf) / v, rel=1e-10)


def test_n_active_threshold(simple_2asset):
    w, mu, Sigma = simple_2asset
    out = _portfolio_metrics(w, mu, Sigma)
    assert out["n_active"] == 2


def test_n_active_zero_weight():
    """A zero weight drops the asset from n_active."""
    w = np.array([0.0, 0.5, 0.5])
    mu = np.array([0.10, 0.12, 0.08])
    Sigma = np.diag([0.04, 0.0225, 0.01])
    out = _portfolio_metrics(w, mu, Sigma)
    assert out["n_active"] == 2


# ── correlated assets ─────────────────────────────────────────────────────────

def test_volatility_correlated():
    """3-asset portfolio with off-diagonal Sigma."""
    w = np.array([1 / 3, 1 / 3, 1 / 3])
    vol = np.array([0.20, 0.15, 0.25])
    rho = 0.4
    Sigma = np.outer(vol, vol) * rho
    np.fill_diagonal(Sigma, vol**2)

    out = _portfolio_metrics(w, np.zeros(3), Sigma)
    expected_var = float(w @ Sigma @ w)
    assert out["volatility"] == pytest.approx(math.sqrt(expected_var), rel=1e-10)


# ── edge cases ────────────────────────────────────────────────────────────────

def test_sharpe_zero_vol():
    """When volatility is effectively 0, sharpe should be 0 (not divide-by-zero)."""
    w = np.array([1.0])
    mu = np.array([0.05])
    Sigma = np.array([[1e-20]])     # effectively zero variance
    out = _portfolio_metrics(w, mu, Sigma)
    assert out["sharpe"] == 0.0


def test_equal_weight_large():
    """Sanity check on a larger universe: return = mean(mu), vol within bounds."""
    n = 10
    np.random.seed(0)
    mu = np.random.uniform(0.05, 0.20, n)
    A = np.random.randn(n, n)
    Sigma = A.T @ A / n + np.eye(n) * 0.01
    w = np.ones(n) / n

    out = _portfolio_metrics(w, mu, Sigma)
    assert out["return"] == pytest.approx(mu.mean(), rel=1e-10)
    assert out["volatility"] > 0
    assert isinstance(out["sharpe"], float)
    assert out["n_active"] == n
