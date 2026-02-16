"""
Unit tests for Quantum Stochastic Walk optimizer.
"""
import pytest
import numpy as np
import pandas as pd

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.quantum_annealing import QuantumAnnealingOptimizer, run_quantum_annealing_comparison
from core.quantum_inspired.evolution_dynamics import QuantumEvolution
from config.qsw_config import QSWConfig
from core.quantum_inspired.quantum_annealing import QAConfig

class TestQuantumWalk:

    def setup_method(self):
        """Set up test fixtures."""
        self.n_assets = 10
        self.returns = np.random.randn(self.n_assets) * 0.1 + 0.05
        self.covariance = self._generate_valid_covariance(self.n_assets)
        self.optimizer = QuantumStochasticWalkOptimizer()

    def _generate_valid_covariance(self, n):
        """Generate a valid positive semi-definite covariance matrix."""
        A = np.random.randn(n, n)
        return np.dot(A.T, A) / n

    def test_initialization(self):
        """Test optimizer initialization."""
        assert self.optimizer.config is not None
        assert self.optimizer.graph_builder is not None
        assert self.optimizer.evolution_engine is not None
        assert self.optimizer.stability_enhancer is not None

    def test_optimization_basic(self):
        """Test basic optimization functionality."""
        result = self.optimizer.optimize(self.returns, self.covariance)

        # Check result structure
        assert result.weights is not None
        assert len(result.weights) == self.n_assets

        # Check weights sum to 1
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-6

        # Check weights are non-negative
        assert np.all(result.weights >= 0)

        # Check metrics
        assert result.expected_return is not None
        assert result.volatility >= 0  # Volatility can be 0 in degenerate cases

    def test_market_regimes(self):
        """Test optimization with different market regimes."""
        regimes = ['bull', 'bear', 'volatile', 'normal']

        results = {}
        for regime in regimes:
            result = self.optimizer.optimize(
                self.returns,
                self.covariance,
                market_regime=regime
            )
            results[regime] = result

        # Different regimes should produce different results
        weights_bull = results['bull'].weights
        weights_bear = results['bear'].weights

        assert not np.allclose(weights_bull, weights_bear)

    def test_turnover_reduction(self):
        """Test turnover reduction functionality."""
        # First optimization
        result1 = self.optimizer.optimize(self.returns, self.covariance)

        # Perturb data slightly
        returns2 = self.returns + np.random.randn(self.n_assets) * 0.01

        # Second optimization with initial weights
        result2 = self.optimizer.optimize(
            returns2,
            self.covariance,
            initial_weights=result1.weights
        )

        # Turnover should be calculated
        assert result2.turnover >= 0
        assert result2.turnover <= 2.0  # Maximum possible turnover

    def test_constraint_application(self):
        """Test portfolio constraints."""
        config = QSWConfig(min_weight=0.05, max_weight=0.20)
        optimizer = QuantumStochasticWalkOptimizer(config)

        result = optimizer.optimize(self.returns, self.covariance)

        # Check constraints are satisfied
        non_zero_weights = result.weights[result.weights > 0.001]
        if len(non_zero_weights) > 0:
            assert np.min(non_zero_weights) >= config.min_weight * 0.9  # Allow small tolerance
            assert np.max(result.weights) <= config.max_weight * 1.1

    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Wrong covariance shape
        bad_covariance = np.random.randn(self.n_assets + 1, self.n_assets + 1)

        with pytest.raises(ValueError):
            self.optimizer.optimize(self.returns, bad_covariance)

    def test_history_tracking(self):
        """Test optimization history tracking."""
        # Run multiple optimizations
        for _ in range(3):
            self.optimizer.optimize(self.returns, self.covariance)

        history = self.optimizer.get_optimization_history()

        assert len(history) == 3
        assert 'sharpe_ratio' in history.columns
        assert 'turnover' in history.columns

    def test_different_evolution_methods(self):
        """Test different quantum evolution methods."""
        # Continuous evolution (original method)
        config_cont = QSWConfig(evolution_method='continuous', evolution_time=10)
        optimizer_cont = QuantumStochasticWalkOptimizer(config_cont)
        result_cont = optimizer_cont.optimize(self.returns, self.covariance)

        # Discrete-time evolution
        config_disc = QSWConfig(evolution_method='discrete', evolution_time=10)
        optimizer_disc = QuantumStochasticWalkOptimizer(config_disc)
        result_disc = optimizer_disc.optimize(self.returns, self.covariance)

        # Decoherent evolution
        config_decoh = QSWConfig(evolution_method='decoherent', evolution_time=10, decoherence_rate=0.15)
        optimizer_decoh = QuantumStochasticWalkOptimizer(config_decoh)
        result_decoh = optimizer_decoh.optimize(self.returns, self.covariance)

        # All should produce valid (finite) results
        assert np.isfinite(result_cont.sharpe_ratio)
        assert np.isfinite(result_disc.sharpe_ratio)
        assert np.isfinite(result_decoh.sharpe_ratio)

        # All weights should sum to 1
        assert abs(np.sum(result_cont.weights) - 1.0) < 1e-6
        assert abs(np.sum(result_disc.weights) - 1.0) < 1e-6
        assert abs(np.sum(result_decoh.weights) - 1.0) < 1e-6

    def test_evolution_dynamics_enhancements(self):
        """Test enhanced evolution dynamics methods."""
        # Create a simple graph for testing
        import networkx as nx
        graph = nx.complete_graph(self.n_assets)
        
        # Add node attributes
        for i in range(self.n_assets):
            graph.nodes[i]['return_potential'] = self.returns[i]
            graph.nodes[i]['risk'] = np.sqrt(self.covariance[i, i])
        
        # Add edge weights based on covariance
        for i in range(self.n_assets):
            for j in range(i+1, self.n_assets):
                weight = abs(self.covariance[i, j]) / (np.sqrt(self.covariance[i, i] * self.covariance[j, j]) + 1e-8)
                graph.edges[i, j]['weight'] = weight

        evolution_engine = QuantumEvolution()

        # Test continuous evolution
        weights_cont, metrics_cont = evolution_engine.evolve(graph, 0.3, 10)

        # Test discrete-time evolution
        weights_disc, metrics_disc = evolution_engine.evolve_discrete_time(graph, 0.3, 10)

        # Test decoherent evolution
        weights_decoh, metrics_decoh = evolution_engine.evolve_with_decoherence(graph, 0.3, 10)

        # All should produce valid weights
        assert len(weights_cont) == self.n_assets
        assert len(weights_disc) == self.n_assets
        assert len(weights_decoh) == self.n_assets

        # All weights should be non-negative and sum to 1
        assert np.all(weights_cont >= 0) and abs(np.sum(weights_cont) - 1.0) < 1e-6
        assert np.all(weights_disc >= 0) and abs(np.sum(weights_disc) - 1.0) < 1e-6
        assert np.all(weights_decoh >= 0) and abs(np.sum(weights_decoh) - 1.0) < 1e-6

        # All should have the expected metrics
        assert 'entropy' in metrics_cont
        assert 'entropy' in metrics_disc
        assert 'entropy' in metrics_decoh

    def test_quantum_annealing_integration(self):
        """Test quantum annealing optimizer integration."""
        qa_optimizer = QuantumAnnealingOptimizer()
        result = qa_optimizer.optimize(self.returns, self.covariance)

        # Check result structure
        assert result['weights'] is not None
        assert len(result['weights']) == self.n_assets

        # Check weights sum to 1
        assert np.abs(np.sum(result['weights']) - 1.0) < 1e-6

        # Check weights are non-negative
        assert np.all(result['weights'] >= 0)

        # Check metrics
        assert result['sharpe_ratio'] >= 0
        assert result['expected_return'] is not None
        assert result['volatility'] > 0

    def test_quantum_annealing_comparison(self):
        """Test quantum annealing vs classical comparison."""
        comparison = run_quantum_annealing_comparison(self.returns, self.covariance)

        assert 'quantum_annealing' in comparison
        assert 'classical' in comparison

        qa_result = comparison['quantum_annealing']
        classical_result = comparison['classical']

        # Both should have valid results
        assert qa_result['sharpe_ratio'] >= 0
        assert classical_result['sharpe_ratio'] >= 0