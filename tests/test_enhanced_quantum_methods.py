"""
Unit tests for notebook-based portfolio optimization methods.
Tests Hybrid, QUBO-SA, VQE, and classical optimizers via run_optimization.
"""
import pytest
import numpy as np

from services.portfolio_optimizer import run_optimization, OBJECTIVES
from core.quantum_inspired.quantum_annealing import (
    QuantumAnnealingOptimizer,
    run_quantum_annealing_comparison,
    QAConfig,
)


class TestNotebookOptimizers:

    def setup_method(self):
        """Set up test fixtures."""
        self.n_assets = 10
        np.random.seed(42)
        self.returns = np.random.randn(self.n_assets) * 0.1 + 0.05
        self.covariance = self._generate_valid_covariance(self.n_assets)

    def _generate_valid_covariance(self, n):
        """Generate a valid positive semi-definite covariance matrix."""
        A = np.random.randn(n, n)
        return np.dot(A.T, A) / n

    @pytest.mark.parametrize("objective", ["hybrid", "qubo_sa", "vqe", "markowitz", "min_variance", "hrp"])
    def test_objective_produces_valid_result(self, objective):
        """Test each objective produces valid portfolio."""
        result = run_optimization(self.returns, self.covariance, objective=objective)
        assert result.weights is not None
        assert len(result.weights) == self.n_assets
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5
        assert np.all(result.weights >= -1e-6)
        assert np.isfinite(result.sharpe_ratio)
        assert result.expected_return is not None
        assert result.volatility > 0

    def test_quantum_annealing_optimizer(self):
        """Test quantum annealing optimizer (legacy, still in core)."""
        qa_optimizer = QuantumAnnealingOptimizer()
        result = qa_optimizer.optimize(self.returns, self.covariance)
        assert result['weights'] is not None
        assert len(result['weights']) == self.n_assets
        assert np.abs(np.sum(result['weights']) - 1.0) < 1e-6
        assert np.all(result['weights'] >= 0)
        assert np.isfinite(result['sharpe_ratio'])

    def test_quantum_annealing_comparison(self):
        """Test quantum annealing vs classical comparison."""
        comparison = run_quantum_annealing_comparison(self.returns, self.covariance)
        assert 'quantum_annealing' in comparison
        assert 'classical' in comparison
        assert np.isfinite(comparison['quantum_annealing']['sharpe_ratio'])
        assert np.isfinite(comparison['classical']['sharpe_ratio'])

    def test_equal_weight_baseline(self):
        """Test equal weight baseline."""
        result = run_optimization(self.returns, self.covariance, objective='equal_weight')
        expected = np.ones(self.n_assets) / self.n_assets
        np.testing.assert_array_almost_equal(result.weights, expected)

    def test_large_portfolio(self):
        """Test performance on larger portfolios."""
        large_n = 50
        large_returns = np.random.randn(large_n) * 0.1 + 0.05
        A = np.random.randn(large_n, large_n)
        large_covariance = np.dot(A.T, A) / large_n
        result = run_optimization(large_returns, large_covariance, objective='hybrid')
        assert np.isfinite(result.sharpe_ratio)
        assert abs(np.sum(result.weights) - 1.0) < 1e-6
        assert len(result.weights) == large_n

    def test_qa_configurations(self):
        """Test different quantum annealing configurations."""
        for config in [
            QAConfig(initial_temperature=50.0, final_temperature=0.05),
            QAConfig(quantum_fluctuation_strength=0.05),
        ]:
            qa_optimizer = QuantumAnnealingOptimizer(config)
            result = qa_optimizer.optimize(self.returns, self.covariance)
            assert len(result['weights']) == self.n_assets
            assert abs(np.sum(result['weights']) - 1.0) < 1e-6


class TestIntegration:

    def setup_method(self):
        """Set up test fixtures."""
        self.n_assets = 8
        np.random.seed(123)
        self.returns = np.random.randn(self.n_assets) * 0.1 + 0.05
        A = np.random.randn(self.n_assets, self.n_assets)
        self.covariance = np.dot(A.T, A) / self.n_assets

    def test_all_methods_produce_valid_results(self):
        """Test complete workflow with all available methods."""
        objectives = ['hybrid', 'qubo_sa', 'vqe', 'markowitz', 'min_variance', 'hrp', 'equal_weight']
        for obj in objectives:
            result = run_optimization(self.returns, self.covariance, objective=obj)
            assert np.isfinite(result.sharpe_ratio)
            assert abs(np.sum(result.weights) - 1.0) < 1e-6

    def test_objectives_config(self):
        """Test OBJECTIVES contains expected keys."""
        expected = {'hybrid', 'qubo_sa', 'vqe', 'markowitz', 'min_variance', 'hrp', 'equal_weight'}
        assert expected.issubset(set(OBJECTIVES.keys()))
