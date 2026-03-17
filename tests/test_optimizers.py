"""
tests/test_optimizers.py

Unit tests for all methods in core/optimizers/.
Uses only synthetic data — no network calls, no yfinance.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from core.optimizers import (
    equal_weight,
    markowitz_max_sharpe,
    min_variance,
    target_return_frontier,
    hrp_weights,
    qubo_sa_weights,
    vqe_weights,
    hybrid_pipeline_weights,
)
from core.portfolio_optimizer import run_optimization, OBJECTIVES


# ── Fixtures ────────────────────────────────────────────────────────────────

def _make_universe(n: int = 8, seed: int = 42):
    """Generate a realistic synthetic universe."""
    rng = np.random.default_rng(seed)
    mu = rng.uniform(0.05, 0.25, n)
    A = rng.standard_normal((n, n))
    Sigma = (A.T @ A) / n + np.eye(n) * 0.01
    # Annualise
    Sigma *= 252 / 252  # already annual in this fixture
    return mu, Sigma


# ── Shared weight validity checks ───────────────────────────────────────────

def _assert_valid_weights(w: np.ndarray, name: str):
    assert w.ndim == 1, f"{name}: weights must be 1-D"
    assert np.all(w >= -1e-8), f"{name}: negative weights found"
    assert abs(w.sum() - 1.0) < 1e-6, f"{name}: weights don't sum to 1 (sum={w.sum():.6f})"
    assert np.all(np.isfinite(w)), f"{name}: non-finite weights"


# ── equal_weight ────────────────────────────────────────────────────────────

class TestEqualWeight:
    def test_equal_allocation(self):
        mu, S = _make_universe(8)
        w = equal_weight(mu, S)
        assert np.allclose(w, 1 / 8)
        _assert_valid_weights(w, "equal_weight")

    def test_different_sizes(self):
        for n in [2, 5, 15, 30]:
            mu, S = _make_universe(n)
            w = equal_weight(mu, S)
            assert len(w) == n
            assert np.allclose(w, 1 / n)


# ── markowitz_max_sharpe ────────────────────────────────────────────────────

class TestMarkowitz:
    def test_weights_valid(self):
        mu, S = _make_universe(8)
        w = markowitz_max_sharpe(mu, S)
        _assert_valid_weights(w, "markowitz")

    def test_sharpe_beats_equal_weight(self):
        mu, S = _make_universe(8, seed=1)
        w_ew = equal_weight(mu, S)
        w_mk = markowitz_max_sharpe(mu, S)
        sr_ew = (w_ew @ mu) / np.sqrt(w_ew @ S @ w_ew)
        sr_mk = (w_mk @ mu) / np.sqrt(w_mk @ S @ w_mk)
        assert sr_mk >= sr_ew - 1e-4, "Markowitz should not underperform 1/N"

    def test_weight_bounds_respected(self):
        mu, S = _make_universe(8)
        w = markowitz_max_sharpe(mu, S, weight_bounds=(0.05, 0.25))
        assert np.all(w <= 0.25 + 1e-6)
        # Only active positions need to respect min bound
        active = w[w > 1e-4]
        assert np.all(active >= 0.05 - 1e-6)


class TestMinVariance:
    def test_weights_valid(self):
        mu, S = _make_universe(8)
        w = min_variance(mu, S)
        _assert_valid_weights(w, "min_variance")

    def test_lower_vol_than_equal_weight(self):
        mu, S = _make_universe(10, seed=3)
        w_ew = equal_weight(mu, S)
        w_mv = min_variance(mu, S)
        vol_ew = np.sqrt(w_ew @ S @ w_ew)
        vol_mv = np.sqrt(w_mv @ S @ w_mv)
        assert vol_mv <= vol_ew + 1e-4


class TestTargetReturnFrontier:
    def test_returns_list_of_dicts(self):
        mu, S = _make_universe(6)
        frontier = target_return_frontier(mu, S, n_points=10)
        assert isinstance(frontier, list)
        assert len(frontier) > 0
        for pt in frontier:
            assert "volatility" in pt
            assert "sharpe" in pt
            assert "weights" in pt

    def test_frontier_vols_roughly_increasing(self):
        mu, S = _make_universe(8)
        frontier = target_return_frontier(mu, S, n_points=15)
        vols = [pt["volatility"] for pt in frontier]
        # First half should have lower vol than second half
        assert np.mean(vols[: len(vols) // 2]) <= np.mean(vols[len(vols) // 2 :]) + 1e-3


# ── hrp ─────────────────────────────────────────────────────────────────────

class TestHRP:
    def test_weights_valid(self):
        mu, S = _make_universe(8)
        w = hrp_weights(mu, S)
        _assert_valid_weights(w, "hrp")

    def test_all_assets_allocated(self):
        mu, S = _make_universe(8)
        w = hrp_weights(mu, S)
        assert np.all(w > 0), "HRP should allocate to all assets"

    def test_lower_concentration_than_equal_weight(self):
        # HRP should be close to 1/N — not wildly concentrated
        mu, S = _make_universe(10)
        w = hrp_weights(mu, S)
        hhi = float(np.sum(w ** 2))
        hhi_ew = 1.0 / 10
        # HRP concentration should be within 3x of 1/N
        assert hhi <= hhi_ew * 3.0


# ── qubo_sa ─────────────────────────────────────────────────────────────────

class TestQUBOSA:
    def test_weights_valid(self):
        mu, S = _make_universe(8)
        w = qubo_sa_weights(mu, S, K=4, n_steps=2000, n_restarts=5)
        _assert_valid_weights(w, "qubo_sa")

    def test_cardinality_respected(self):
        mu, S = _make_universe(8)
        for K in [2, 3, 4]:
            w = qubo_sa_weights(mu, S, K=K, n_steps=2000, n_restarts=5)
            n_active = int(np.sum(w > 1e-4))
            assert n_active == K, f"Expected K={K} active, got {n_active}"

    def test_equal_weight_within_selection(self):
        mu, S = _make_universe(8)
        K = 3
        w = qubo_sa_weights(mu, S, K=K, n_steps=2000, n_restarts=5)
        active_weights = w[w > 1e-4]
        # All active weights should be 1/K
        assert np.allclose(active_weights, 1.0 / K, atol=1e-6)

    def test_reproducible_with_seed(self):
        mu, S = _make_universe(8)
        w1 = qubo_sa_weights(mu, S, K=4, seed=99)
        w2 = qubo_sa_weights(mu, S, K=4, seed=99)
        assert np.allclose(w1, w2)


# ── vqe ─────────────────────────────────────────────────────────────────────

class TestVQE:
    def test_weights_valid(self):
        mu, S = _make_universe(6)
        w = vqe_weights(mu, S, n_layers=2, n_restarts=3)
        _assert_valid_weights(w, "vqe")

    def test_weight_bounds_respected(self):
        mu, S = _make_universe(6)
        w = vqe_weights(mu, S, weight_min=0.05, weight_max=0.25, n_restarts=3)
        active = w[w > 1e-4]
        assert np.all(active >= 0.05 - 1e-5)
        assert np.all(active <= 0.25 + 1e-5)

    def test_reproducible_with_seed(self):
        mu, S = _make_universe(6)
        w1 = vqe_weights(mu, S, n_restarts=3, seed=7)
        w2 = vqe_weights(mu, S, n_restarts=3, seed=7)
        assert np.allclose(w1, w2)


# ── hybrid_pipeline ──────────────────────────────────────────────────────────

class TestHybridPipeline:
    def test_weights_valid(self):
        mu, S = _make_universe(10)
        w, info = hybrid_pipeline_weights(mu, S, K_screen=6, K_select=3)
        _assert_valid_weights(w, "hybrid")

    def test_stage_info_populated(self):
        mu, S = _make_universe(10)
        w, info = hybrid_pipeline_weights(mu, S, K_screen=6, K_select=3)
        assert len(info.stage1_screened_idx) == 6
        assert len(info.stage2_selected_idx) == 3
        assert isinstance(info.stage2_qubo_obj, float)
        assert isinstance(info.stage3_sharpe, float)

    def test_only_selected_assets_have_weight(self):
        mu, S = _make_universe(10)
        w, info = hybrid_pipeline_weights(mu, S, K_screen=6, K_select=3)
        active_idx = set(np.where(w > 1e-4)[0].tolist())
        selected_idx = set(info.stage2_selected_idx)
        assert active_idx == selected_idx

    def test_k_select_cardinality(self):
        mu, S = _make_universe(12)
        for K_sel in [2, 4, 5]:
            w, info = hybrid_pipeline_weights(
                mu, S, K_screen=8, K_select=K_sel, n_sa_restarts=5
            )
            assert len(info.stage2_selected_idx) == K_sel


# ── run_optimization (service layer) ────────────────────────────────────────

class TestRunOptimization:
    @pytest.fixture
    def universe(self):
        return _make_universe(8)

    def test_all_objectives_run(self, universe):
        mu, S = universe
        for obj in OBJECTIVES:
            kwargs = {}
            if obj == "target_return":
                kwargs["target_return"] = float(np.mean(mu))
            result = run_optimization(mu, S, objective=obj, **kwargs)
            _assert_valid_weights(result.weights, obj)
            assert result.objective == obj

    def test_invalid_objective_raises(self, universe):
        mu, S = universe
        with pytest.raises(ValueError, match="Unknown objective"):
            run_optimization(mu, S, objective="quantum_magic")

    def test_hybrid_stage_info_returned(self, universe):
        mu, S = universe
        result = run_optimization(mu, S, objective="hybrid")
        assert result.stage_info is not None
        assert "stage2_selected_idx" in result.stage_info

    def test_target_return_without_value_raises(self, universe):
        mu, S = universe
        with pytest.raises(ValueError, match="target_return"):
            run_optimization(mu, S, objective="target_return")

    def test_asset_names_propagated(self, universe):
        mu, S = universe
        names = [f"A{i}" for i in range(len(mu))]
        result = run_optimization(mu, S, objective="markowitz", asset_names=names)
        assert result.asset_names == names

    def test_hybrid_stage_info_contains_names(self, universe):
        mu, S = universe
        names = [f"TICKER{i}" for i in range(len(mu))]
        result = run_optimization(mu, S, objective="hybrid", asset_names=names)
        assert isinstance(result.stage_info["stage2_selected_names"][0], str)
