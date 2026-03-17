"""Tests for the methods package — portfolio optimization methods from research notebooks."""
import numpy as np
import pytest

from methods import (
    equal_weight,
    hrp_weights,
    hybrid_pipeline_weights,
    markowitz_max_sharpe,
    min_variance,
    qubo_sa_weights,
    target_return_frontier,
    vqe_weights,
)
from methods.hybrid_pipeline import HybridPipelineInfo


def _sample_data():
    """15-asset dataset matching notebook 05 (seeded for reproducibility)."""
    np.random.seed(2025)
    n = 15
    mu = np.array(
        [
            0.18, 0.20, 0.15, 0.22, 0.17, 0.35,
            0.12, 0.13, 0.16, 0.18,
            0.08, 0.14, 0.10,
            0.10, 0.09,
        ]
    )
    sigma_vec = np.array(
        [
            0.28, 0.25, 0.24, 0.30, 0.35, 0.42,
            0.20, 0.22, 0.22, 0.24,
            0.16, 0.18, 0.20,
            0.22, 0.24,
        ]
    )
    corr = np.full((n, n), 0.30)
    np.fill_diagonal(corr, 1.0)
    for start, size in [(0, 6), (6, 4), (10, 3), (13, 2)]:
        for i in range(start, start + size):
            for j in range(start, start + size):
                if i != j:
                    corr[i, j] = 0.68
    noise = np.random.uniform(-0.04, 0.04, (n, n))
    noise = (noise + noise.T) / 2
    np.fill_diagonal(noise, 0)
    corr = np.clip(corr + noise, -0.95, 0.95)
    np.fill_diagonal(corr, 1.0)
    Sigma = np.outer(sigma_vec, sigma_vec) * corr
    eig = np.linalg.eigvalsh(Sigma)
    if np.any(eig < 0):
        Sigma += (-eig.min() + 1e-6) * np.eye(n)
    return mu, Sigma


class TestWeightsSumToOne:
    """All methods must return weights summing to ~1."""

    @pytest.fixture
    def data(self):
        return _sample_data()

    def test_equal_weight(self, data):
        mu, Sigma = data
        w = equal_weight(mu, Sigma)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)

    def test_markowitz_max_sharpe(self, data):
        mu, Sigma = data
        w = markowitz_max_sharpe(mu, Sigma)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)

    def test_min_variance(self, data):
        mu, Sigma = data
        w = min_variance(mu, Sigma)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)

    def test_hrp_weights(self, data):
        mu, Sigma = data
        w = hrp_weights(mu, Sigma)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)

    def test_qubo_sa_weights(self, data):
        mu, Sigma = data
        w = qubo_sa_weights(mu, Sigma, K=6)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)
        assert np.sum(w > 0) == 6

    def test_vqe_weights(self, data):
        mu, Sigma = data
        w = vqe_weights(mu, Sigma, n_restarts=3)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)

    def test_hybrid_pipeline_weights(self, data):
        mu, Sigma = data
        w, info = hybrid_pipeline_weights(mu, Sigma, K_screen=10, K_select=5)
        assert np.isclose(w.sum(), 1.0)
        assert len(w) == len(mu)
        assert np.sum(w > 0) == 5


class TestTargetReturnFrontier:
    """target_return_frontier returns correct structure."""

    def test_frontier_structure(self):
        mu, Sigma = _sample_data()
        frontier = target_return_frontier(mu, Sigma, n_points=5)
        assert isinstance(frontier, list)
        assert len(frontier) >= 1
        for pt in frontier:
            assert "target_return" in pt
            assert "volatility" in pt
            assert "sharpe" in pt
            assert "weights" in pt
            assert len(pt["weights"]) == len(mu)
            assert np.isclose(sum(pt["weights"]), 1.0)


class TestHybridPipelineInfo:
    """hybrid_pipeline_weights returns (weights, info) with correct shapes."""

    def test_info_keys(self):
        mu, Sigma = _sample_data()
        w, info = hybrid_pipeline_weights(mu, Sigma, K_screen=10, K_select=5)
        assert len(info.stage1_screened_idx) == 10
        assert info.stage1_ic is not None
        assert len(info.stage2_selected_idx) == 5
        assert hasattr(info, "stage2_qubo_obj")
        assert hasattr(info, "stage3_sharpe")

    def test_info_indices_valid(self):
        mu, Sigma = _sample_data()
        w, info = hybrid_pipeline_weights(mu, Sigma, K_screen=8, K_select=4)
        assert all(isinstance(i, int) for i in info.stage1_screened_idx)
        assert all(isinstance(i, int) for i in info.stage2_selected_idx)
        assert all(0 <= i < len(mu) for i in info.stage1_screened_idx)
        assert all(0 <= i < len(mu) for i in info.stage2_selected_idx)


class TestSmoke:
    """Basic smoke test: run each method on the 15-asset dataset."""

    def test_all_methods_run(self):
        mu, Sigma = _sample_data()
        methods = [
            lambda: equal_weight(mu, Sigma),
            lambda: markowitz_max_sharpe(mu, Sigma),
            lambda: min_variance(mu, Sigma),
            lambda: hrp_weights(mu, Sigma),
            lambda: qubo_sa_weights(mu, Sigma, K=6),
            lambda: vqe_weights(mu, Sigma, n_restarts=2),
            lambda: hybrid_pipeline_weights(mu, Sigma, K_screen=10, K_select=5)[0],
        ]
        for fn in methods:
            w = fn()
            assert w is not None
            assert isinstance(w, np.ndarray)
            assert len(w) == 15
            assert np.all(w >= -1e-6)
            assert np.isclose(w.sum(), 1.0, rtol=1e-5)
