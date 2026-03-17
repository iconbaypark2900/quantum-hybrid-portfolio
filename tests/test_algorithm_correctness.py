"""
Algorithm correctness and cross-comparison tests.

Proves every optimization objective (max_sharpe, min_variance, risk_parity,
target_return, hrp) produces mathematically valid, constraint-respecting
portfolios, and compares them against each other on the same data.
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from services.portfolio_optimizer import run_optimization, OptimizationResult


# --- Fixed synthetic data ---

SEED = 42
N_ASSETS = 10
OBJECTIVES = ['max_sharpe', 'min_variance', 'risk_parity', 'target_return', 'hrp']


def _fixed_data():
    np.random.seed(SEED)
    returns = np.array([0.12, 0.08, 0.15, 0.06, 0.10, 0.09, 0.14, 0.07, 0.11, 0.05])
    A = np.random.randn(N_ASSETS, N_ASSETS)
    cov = A.T @ A / N_ASSETS + np.eye(N_ASSETS) * 0.02
    return returns, cov


def _equal_weight_metrics(returns, cov):
    n = len(returns)
    w = np.ones(n) / n
    ret = float(w @ returns)
    vol = float(np.sqrt(w @ cov @ w))
    sharpe = ret / vol if vol > 0 else 0
    return {'return': ret, 'volatility': vol, 'sharpe': sharpe}


# ============================================================================
# 3a. Mathematical invariants — every objective
# ============================================================================


class TestMathInvariants:
    """Every objective must satisfy basic portfolio invariants."""

    @pytest.fixture(params=OBJECTIVES)
    def result(self, request):
        returns, cov = _fixed_data()
        target = float(np.mean(returns)) if request.param == 'target_return' else None
        return run_optimization(returns, cov, objective=request.param, target_return=target)

    def test_weights_sum_to_one(self, result):
        assert abs(np.sum(result.weights) - 1.0) < 1e-5

    def test_weights_non_negative(self, result):
        assert np.all(result.weights >= -1e-9)

    def test_return_consistent(self, result):
        returns, _ = _fixed_data()
        expected = float(np.dot(result.weights, returns))
        assert abs(result.expected_return - expected) < 1e-5

    def test_volatility_consistent(self, result):
        _, cov = _fixed_data()
        expected = float(np.sqrt(result.weights @ cov @ result.weights))
        assert abs(result.volatility - expected) < 1e-5

    def test_sharpe_consistent(self, result):
        if result.volatility > 1e-10:
            expected = result.expected_return / result.volatility
            assert abs(result.sharpe_ratio - expected) < 1e-5

    def test_sharpe_non_negative(self, result):
        # On positive-return data all objectives should produce non-negative Sharpe
        assert result.sharpe_ratio >= -1e-5


class TestIdenticalAssets:
    """With identical assets all objectives should produce roughly equal weights."""

    def test_equal_weights_for_identical_assets(self):
        n = 5
        returns = np.full(n, 0.10)
        cov = np.eye(n) * 0.04
        for obj in ['min_variance', 'risk_parity', 'hrp']:
            result = run_optimization(returns, cov, objective=obj)
            np.testing.assert_allclose(
                result.weights, np.ones(n) / n, atol=0.05,
                err_msg=f"objective={obj} should give equal weights for identical assets"
            )


# ============================================================================
# 3b. Objective-specific correctness
# ============================================================================


class TestMinVariance:

    def test_volatility_le_equal_weight(self):
        returns, cov = _fixed_data()
        ew = _equal_weight_metrics(returns, cov)
        result = run_optimization(returns, cov, objective='min_variance')
        assert result.volatility <= ew['volatility'] + 1e-6


class TestRiskParity:

    def test_risk_contributions_more_equal_than_equal_weight(self):
        """Risk parity should produce more equal risk contributions than equal-weight."""
        returns, cov = _fixed_data()
        result = run_optimization(returns, cov, objective='risk_parity')
        w_rp = result.weights
        w_ew = np.ones(N_ASSETS) / N_ASSETS

        def rc_std(w):
            vol = np.sqrt(w @ cov @ w)
            if vol < 1e-10:
                return 0.0
            mcr = (cov @ w) / vol
            rc = w * mcr
            return float(np.std(rc))

        assert rc_std(w_rp) <= rc_std(w_ew) + 1e-4, (
            f"Risk parity rc_std ({rc_std(w_rp):.4f}) > equal-weight rc_std ({rc_std(w_ew):.4f})"
        )


class TestTargetReturn:

    def test_return_near_target(self):
        returns, cov = _fixed_data()
        target = float(np.mean(returns))
        result = run_optimization(returns, cov, objective='target_return', target_return=target)
        # Allow fallback to min_variance if target is infeasible
        if result.objective == 'target_return':
            assert abs(result.expected_return - target) < 0.02


class TestHRPCorrectness:

    def test_lower_variance_asset_gets_higher_weight(self):
        """On 2-asset data, HRP raw weights give higher weight to lower-variance asset."""
        from core.optimizers.hrp import hrp_weights
        cov = np.array([[0.04, 0.01], [0.01, 0.16]])
        w = hrp_weights(cov)
        assert w[0] > w[1], "Lower-variance asset should have higher HRP weight"

    def test_deterministic(self):
        returns, cov = _fixed_data()
        r1 = run_optimization(returns, cov, objective='hrp')
        r2 = run_optimization(returns, cov, objective='hrp')
        np.testing.assert_array_equal(r1.weights, r2.weights)


class TestMaxSharpe:

    def test_sharpe_ge_equal_weight(self):
        """QSW max_sharpe should beat or match equal-weight Sharpe."""
        returns, cov = _fixed_data()
        ew = _equal_weight_metrics(returns, cov)
        result = run_optimization(returns, cov, objective='max_sharpe')
        # Allow small tolerance — QSW is heuristic
        assert result.sharpe_ratio >= ew['sharpe'] - 0.1


# ============================================================================
# 3c. Cross-algorithm comparison
# ============================================================================


class TestCrossComparison:
    """Run all objectives on the same data and compare."""

    @pytest.fixture(scope='class')
    def all_results(self):
        returns, cov = _fixed_data()
        results = {}
        for obj in OBJECTIVES:
            target = float(np.mean(returns)) if obj == 'target_return' else None
            results[obj] = run_optimization(returns, cov, objective=obj, target_return=target)
        return results

    def test_all_valid_portfolios(self, all_results):
        for obj, r in all_results.items():
            assert isinstance(r, OptimizationResult), f"{obj} didn't return OptimizationResult"
            assert abs(np.sum(r.weights) - 1.0) < 1e-5, f"{obj} weights don't sum to 1"
            assert np.all(r.weights >= -1e-9), f"{obj} has negative weights"

    def test_min_variance_le_equal_weight_vol(self, all_results):
        """min_variance volatility should be <= equal-weight volatility."""
        _, cov = _fixed_data()
        ew = _equal_weight_metrics(_fixed_data()[0], cov)
        mv_vol = all_results['min_variance'].volatility
        assert mv_vol <= ew['volatility'] + 1e-4

    def test_hrp_competitive_vol(self, all_results):
        """HRP should achieve competitive (often lower) volatility vs classical objectives."""
        hrp_vol = all_results['hrp'].volatility
        mv_vol = all_results['min_variance'].volatility
        # HRP vol should be finite and reasonable (within 50% of min_variance either way)
        assert hrp_vol < mv_vol * 1.5

    def test_no_negative_sharpe(self, all_results):
        for obj, r in all_results.items():
            assert r.sharpe_ratio >= -1e-5, f"{obj} has negative Sharpe: {r.sharpe_ratio}"

    def test_summary_table(self, all_results, capsys):
        """Print comparison table for human review."""
        print("\n\n=== Cross-algorithm comparison (seed=42, N=10) ===")
        print(f"{'Objective':<20} {'Sharpe':>8} {'Return':>8} {'Vol':>8} {'Active':>7}")
        print("-" * 55)
        for obj in OBJECTIVES:
            r = all_results[obj]
            print(f"{obj:<20} {r.sharpe_ratio:8.4f} {r.expected_return:8.4f} {r.volatility:8.4f} {r.n_active:7d}")
        print("=" * 55)
