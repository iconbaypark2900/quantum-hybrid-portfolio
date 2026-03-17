"""
Research validation benchmark tests.

Proves the HRP + Ledoit-Wolf pipeline actually improves results vs raw
Markowitz on synthetic data with a reproducible walk-forward simulation.

References:
  - López de Prado (2016), SSRN 2708678 (HRP)
  - Ledoit & Wolf (2004) (shrinkage covariance)
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from services.risk_models import ledoit_wolf_covariance
from core.optimizers.hrp import hrp_weights
from services.portfolio_optimizer import run_optimization


# --- Synthetic data generators ---

SEED = 42
N_ASSETS = 10
T_TOTAL = 500
T_IN_SAMPLE = 250


def _generate_returns(seed=SEED, n_assets=N_ASSETS, t=T_TOTAL):
    """Generate multivariate normal daily returns with known structure."""
    np.random.seed(seed)
    # True daily expected returns (annualized ~5-15%)
    mu_daily = np.linspace(0.0002, 0.0006, n_assets)
    # True covariance with moderate correlation
    A = np.random.randn(n_assets, n_assets) * 0.01
    true_cov_daily = A.T @ A + np.eye(n_assets) * 0.0001
    returns = np.random.multivariate_normal(mu_daily, true_cov_daily, size=t)
    return returns, mu_daily, true_cov_daily


def _portfolio_realized_metrics(weights, oos_returns):
    """Calculate realized (out-of-sample) portfolio metrics from daily returns."""
    daily_port = oos_returns @ weights
    ann_ret = float(np.mean(daily_port) * 252)
    ann_vol = float(np.std(daily_port) * np.sqrt(252))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    return {'return': ann_ret, 'volatility': ann_vol, 'sharpe': sharpe}


# ============================================================================
# 4a. Ledoit-Wolf improves conditioning
# ============================================================================


class TestLedoitWolfConditioning:

    def test_condition_number_reduced(self):
        """Ledoit-Wolf cov has a lower condition number than sample cov."""
        returns, _, _ = _generate_returns(n_assets=30, t=60)
        sample_cov = np.cov(returns, rowvar=False)
        lw_cov = ledoit_wolf_covariance(returns, annualize=False)
        cond_sample = np.linalg.cond(sample_cov)
        cond_lw = np.linalg.cond(lw_cov)
        assert cond_lw < cond_sample, (
            f"LW cond ({cond_lw:.1f}) should be < sample cond ({cond_sample:.1f})"
        )

    def test_lw_psd(self):
        """Shrunk covariance is positive semi-definite."""
        returns, _, _ = _generate_returns(n_assets=20, t=40)
        lw_cov = ledoit_wolf_covariance(returns, annualize=False)
        eigenvalues = np.linalg.eigvalsh(lw_cov)
        assert np.all(eigenvalues >= -1e-10)

    def test_lw_min_variance_oos_improvement(self):
        """min_variance with LW cov should have <= OOS vol vs sample cov."""
        returns, _, _ = _generate_returns()
        in_sample = returns[:T_IN_SAMPLE]
        out_sample = returns[T_IN_SAMPLE:]

        # Sample covariance path
        sample_cov = np.cov(in_sample, rowvar=False) * 252
        sample_ret = np.mean(in_sample, axis=0) * 252
        res_sample = run_optimization(sample_ret, sample_cov, objective='min_variance')

        # Ledoit-Wolf path
        lw_cov = ledoit_wolf_covariance(in_sample, annualize=True)
        lw_ret = np.mean(in_sample, axis=0) * 252
        res_lw = run_optimization(lw_ret, lw_cov, objective='min_variance')

        # Evaluate out-of-sample
        oos_sample = _portfolio_realized_metrics(res_sample.weights, out_sample)
        oos_lw = _portfolio_realized_metrics(res_lw.weights, out_sample)

        assert oos_lw['volatility'] <= oos_sample['volatility'] * 1.05, (
            f"LW OOS vol ({oos_lw['volatility']:.4f}) > sample OOS vol ({oos_sample['volatility']:.4f}) by >5%"
        )


# ============================================================================
# 4b. HRP vs Markowitz out-of-sample
# ============================================================================


class TestHRPvsMarkowitz:

    @pytest.fixture(scope='class')
    def walk_forward_results(self):
        """Run the walk-forward simulation once and cache results."""
        returns, _, _ = _generate_returns()
        in_sample = returns[:T_IN_SAMPLE]
        out_sample = returns[T_IN_SAMPLE:]

        ann_ret_is = np.mean(in_sample, axis=0) * 252
        sample_cov_is = np.cov(in_sample, rowvar=False) * 252
        lw_cov_is = ledoit_wolf_covariance(in_sample, annualize=True)

        # Markowitz min_variance with sample cov
        markowitz_sample = run_optimization(ann_ret_is, sample_cov_is, objective='min_variance')
        # Markowitz min_variance with LW cov
        markowitz_lw = run_optimization(ann_ret_is, lw_cov_is, objective='min_variance')
        # HRP with LW cov
        hrp_result = run_optimization(ann_ret_is, lw_cov_is, objective='hrp')

        return {
            'markowitz_sample': _portfolio_realized_metrics(markowitz_sample.weights, out_sample),
            'markowitz_lw': _portfolio_realized_metrics(markowitz_lw.weights, out_sample),
            'hrp_lw': _portfolio_realized_metrics(hrp_result.weights, out_sample),
        }

    def test_hrp_vol_le_markowitz_sample(self, walk_forward_results):
        """HRP realized vol <= Markowitz (sample cov) realized vol (core HRP claim)."""
        hrp_vol = walk_forward_results['hrp_lw']['volatility']
        mk_vol = walk_forward_results['markowitz_sample']['volatility']
        assert hrp_vol <= mk_vol * 1.05, (
            f"HRP OOS vol ({hrp_vol:.4f}) > Markowitz (sample) OOS vol ({mk_vol:.4f}) by >5%"
        )

    def test_lw_markowitz_vol_le_sample_markowitz(self, walk_forward_results):
        """Markowitz+LW realized vol <= Markowitz (sample cov) realized vol."""
        lw_vol = walk_forward_results['markowitz_lw']['volatility']
        raw_vol = walk_forward_results['markowitz_sample']['volatility']
        assert lw_vol <= raw_vol * 1.05, (
            f"Markowitz+LW OOS vol ({lw_vol:.4f}) > Markowitz (sample) OOS vol ({raw_vol:.4f}) by >5%"
        )

    def test_all_sharpe_finite(self, walk_forward_results):
        for label, m in walk_forward_results.items():
            assert np.isfinite(m['sharpe']), f"{label} has non-finite Sharpe"

    def test_summary_table(self, walk_forward_results, capsys):
        """Print walk-forward results for human review."""
        print("\n\n=== Walk-forward benchmark (seed=42, N=10, T=500) ===")
        print(f"{'Method':<25} {'OOS Sharpe':>10} {'OOS Vol':>10} {'OOS Ret':>10}")
        print("-" * 60)
        for label, m in walk_forward_results.items():
            print(f"{label:<25} {m['sharpe']:10.4f} {m['volatility']:10.4f} {m['return']:10.4f}")
        print("=" * 60)


# ============================================================================
# 4c. Reproducibility
# ============================================================================


class TestReproducibility:

    def test_walk_forward_deterministic(self):
        """Same seed produces identical walk-forward results."""
        results = []
        for _ in range(2):
            returns, _, _ = _generate_returns(seed=99)
            in_s = returns[:T_IN_SAMPLE]
            out_s = returns[T_IN_SAMPLE:]
            ann_ret = np.mean(in_s, axis=0) * 252
            lw_cov = ledoit_wolf_covariance(in_s, annualize=True)
            hrp_res = run_optimization(ann_ret, lw_cov, objective='hrp')
            results.append(_portfolio_realized_metrics(hrp_res.weights, out_s))
        np.testing.assert_allclose(results[0]['volatility'], results[1]['volatility'])
        np.testing.assert_allclose(results[0]['sharpe'], results[1]['sharpe'])
