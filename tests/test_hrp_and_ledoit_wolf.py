"""
Tests for Ledoit-Wolf covariance shrinkage and Hierarchical Risk Parity (HRP).
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from services.risk_models import ledoit_wolf_covariance
from services.hrp import hrp_weights
from services.portfolio_optimizer import run_optimization, OptimizationResult
from services.constraints import PortfolioConstraints


# --- Helpers ---

def _make_daily_returns(n_assets: int = 5, n_days: int = 252, seed: int = 42):
    """Generate a (T, N) matrix of daily returns."""
    np.random.seed(seed)
    return np.random.randn(n_days, n_assets) * 0.01 + 0.0003


def _make_returns_covariance(n_assets: int = 5, seed: int = 42):
    """Generate annualized returns and a valid PSD covariance matrix."""
    np.random.seed(seed)
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets)
    covariance = np.dot(A.T, A) / n_assets + np.eye(n_assets) * 0.01
    return returns.astype(float), covariance.astype(float)


# ============================================================================
# 1. Ledoit-Wolf covariance tests
# ============================================================================


class TestLedoitWolfCovariance:
    """Tests for services.risk_models.ledoit_wolf_covariance."""

    def test_shape_matches_input(self):
        """Output shape is (N, N) matching number of assets."""
        daily = _make_daily_returns(n_assets=8)
        cov = ledoit_wolf_covariance(daily, annualize=False)
        assert cov.shape == (8, 8)

    def test_symmetric(self):
        """Covariance matrix is symmetric."""
        daily = _make_daily_returns(n_assets=6)
        cov = ledoit_wolf_covariance(daily, annualize=False)
        np.testing.assert_allclose(cov, cov.T, atol=1e-12)

    def test_positive_semidefinite(self):
        """All eigenvalues are non-negative (PSD)."""
        daily = _make_daily_returns(n_assets=10)
        cov = ledoit_wolf_covariance(daily, annualize=False)
        eigenvalues = np.linalg.eigvalsh(cov)
        assert np.all(eigenvalues >= -1e-10), f"Negative eigenvalue: {eigenvalues.min()}"

    def test_annualize_scales_correctly(self):
        """Annualized cov is ~252x the daily cov."""
        daily = _make_daily_returns(n_assets=4)
        cov_daily = ledoit_wolf_covariance(daily, annualize=False)
        cov_annual = ledoit_wolf_covariance(daily, annualize=True)
        np.testing.assert_allclose(cov_annual, cov_daily * 252, atol=1e-12)

    def test_differs_from_sample_cov(self):
        """Shrunk cov differs from the raw sample cov (shrinkage > 0)."""
        daily = _make_daily_returns(n_assets=5, n_days=60)
        cov_shrunk = ledoit_wolf_covariance(daily, annualize=False)
        cov_sample = np.cov(daily, rowvar=False)
        assert not np.allclose(cov_shrunk, cov_sample, atol=1e-8), (
            "Shrunk cov should differ from sample cov"
        )

    def test_single_asset(self):
        """Works with a single asset."""
        daily = _make_daily_returns(n_assets=1)
        cov = ledoit_wolf_covariance(daily, annualize=True)
        assert cov.shape == (1, 1)
        assert cov[0, 0] > 0


# ============================================================================
# 2. HRP algorithm tests
# ============================================================================


class TestHRPWeights:
    """Tests for services.hrp.hrp_weights."""

    def test_weights_sum_to_one(self):
        """HRP weights sum to 1."""
        _, cov = _make_returns_covariance(n_assets=8)
        w = hrp_weights(cov)
        assert abs(w.sum() - 1.0) < 1e-10

    def test_weights_non_negative(self):
        """HRP weights are all non-negative."""
        _, cov = _make_returns_covariance(n_assets=10)
        w = hrp_weights(cov)
        assert np.all(w >= -1e-10)

    def test_shape_matches_input(self):
        """Output length equals number of assets."""
        _, cov = _make_returns_covariance(n_assets=6)
        w = hrp_weights(cov)
        assert len(w) == 6

    def test_single_asset(self):
        """Single-asset case returns weight 1.0."""
        cov = np.array([[0.04]])
        w = hrp_weights(cov)
        np.testing.assert_allclose(w, [1.0])

    def test_two_assets(self):
        """Two-asset HRP gives inverse-variance weighting."""
        cov = np.array([[0.04, 0.01],
                        [0.01, 0.16]])
        w = hrp_weights(cov)
        assert abs(w.sum() - 1.0) < 1e-10
        # Lower-variance asset should get higher weight
        assert w[0] > w[1], "Lower-variance asset should have higher weight"

    def test_all_same_variance(self):
        """Equal-variance uncorrelated assets get roughly equal weights."""
        n = 5
        cov = np.eye(n) * 0.04
        w = hrp_weights(cov)
        np.testing.assert_allclose(w, np.ones(n) / n, atol=0.05)

    def test_deterministic(self):
        """Same input produces same output (no randomness)."""
        _, cov = _make_returns_covariance(n_assets=7, seed=99)
        w1 = hrp_weights(cov)
        w2 = hrp_weights(cov)
        np.testing.assert_array_equal(w1, w2)


# ============================================================================
# 3. HRP integration via portfolio_optimizer
# ============================================================================


class TestHRPOptimizer:
    """Tests for HRP as an objective in run_optimization."""

    def test_hrp_weights_sum_to_one(self):
        """HRP via run_optimization produces weights that sum to 1.0."""
        returns, cov = _make_returns_covariance(6)
        result = run_optimization(returns, cov, objective="hrp")
        assert isinstance(result, OptimizationResult)
        assert abs(np.sum(result.weights) - 1.0) < 1e-5
        assert result.objective == "hrp"

    def test_hrp_alias(self):
        """The long-form alias 'hierarchical_risk_parity' also works."""
        returns, cov = _make_returns_covariance(6)
        result = run_optimization(returns, cov, objective="hierarchical_risk_parity")
        assert result.objective == "hrp"

    def test_hrp_non_negative(self):
        """HRP weights are non-negative."""
        returns, cov = _make_returns_covariance(8)
        result = run_optimization(returns, cov, objective="hrp")
        assert np.all(result.weights >= -1e-9)

    def test_hrp_metrics_consistent(self):
        """Return, vol, and Sharpe are consistent with weights and covariance."""
        returns, cov = _make_returns_covariance(5)
        result = run_optimization(returns, cov, objective="hrp")
        expected_ret = float(np.dot(result.weights, returns))
        expected_vol = float(np.sqrt(result.weights @ cov @ result.weights))
        assert abs(result.expected_return - expected_ret) < 1e-6
        assert abs(result.volatility - expected_vol) < 1e-6

    def test_hrp_with_sector_constraints(self):
        """HRP respects sector constraints."""
        n = 6
        returns, cov = _make_returns_covariance(n)
        sectors = ["Tech", "Tech", "Finance", "Finance", "Energy", "Energy"]
        constraints = PortfolioConstraints(
            sector_limits={"Tech": 0.30}
        )
        result = run_optimization(
            returns, cov,
            objective="hrp",
            constraints=constraints,
            sectors=sectors,
            asset_names=[f"A{i}" for i in range(n)],
        )
        tech_weight = result.weights[0] + result.weights[1]
        assert tech_weight <= 0.30 + 1e-5
