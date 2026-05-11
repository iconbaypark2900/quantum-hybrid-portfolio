"""
tests/test_factor_models.py — unit tests for services/factor_models.py.

Covers:
  - factor score shape and column names
  - z-score invariant (mean ≈ 0 per factor)
  - diversification ratio computed dynamically, not hardcoded to 0.75
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pytest

from services.factor_models import (
    compute_factor_scores,
    compute_portfolio_factor_exposure,
)


N = 8
_RNG = np.random.default_rng(42)
_MU = _RNG.uniform(0.05, 0.20, size=N)
_VOLS = _RNG.uniform(0.10, 0.40, size=N)
_SIGMA_DIAG = _VOLS ** 2
_WEIGHTS = np.ones(N) / N


class TestFactorScoresShape:
    def test_shape_and_columns(self):
        scores = compute_factor_scores(_MU, _SIGMA_DIAG)
        assert scores.shape == (N, 4), f"Expected ({N}, 4), got {scores.shape}"
        expected_cols = {"market_beta", "size", "momentum", "low_vol"}
        assert set(scores.columns) == expected_cols

    def test_asset_names_as_index(self):
        names = [f"ASSET{i}" for i in range(N)]
        scores = compute_factor_scores(_MU, _SIGMA_DIAG, asset_names=names)
        assert list(scores.index) == names


class TestFactorScoresZScored:
    def test_column_means_near_zero(self):
        scores = compute_factor_scores(_MU, _SIGMA_DIAG)
        for col in scores.columns:
            mean_val = float(scores[col].mean())
            assert abs(mean_val) < 1e-6, (
                f"Factor '{col}' mean={mean_val:.2e} is not near 0 — z-score invariant violated"
            )

    def test_no_nan_or_inf(self):
        scores = compute_factor_scores(_MU, _SIGMA_DIAG)
        assert not scores.isna().any().any(), "Factor scores contain NaN"
        assert np.isfinite(scores.values).all(), "Factor scores contain Inf"


try:
    from core.quantum_inspired.advanced_quantum_optimizer import run_advanced_comparison
    _ADVANCED_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _ADVANCED_AVAILABLE = False


@pytest.mark.skipif(
    not _ADVANCED_AVAILABLE,
    reason="core.quantum_inspired.advanced_quantum_optimizer not importable (missing optional deps)",
)
class TestDiversificationRatioNotPlaceholder:
    def test_standard_qsw_diversification_ratio_is_computed(self):
        """run_advanced_comparison must return a computed DR, not the old 0.75 literal."""
        n = 5
        rng = np.random.default_rng(0)
        mu = rng.uniform(0.06, 0.15, size=n)
        vols = rng.uniform(0.12, 0.30, size=n)
        corr = np.eye(n) + 0.3 * (np.ones((n, n)) - np.eye(n))
        cov = np.outer(vols, vols) * corr

        result = run_advanced_comparison(mu, cov)
        dr = result["standard_qsw"]["diversification_ratio"]

        assert dr != 0.75, (
            f"diversification_ratio is still the old placeholder 0.75 — computation not applied"
        )
        assert 0.5 < dr < 10.0, (
            f"diversification_ratio={dr} is outside plausible range (0.5, 10)"
        )
