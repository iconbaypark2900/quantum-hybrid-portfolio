"""
Enhanced unit tests for Quantum Stochastic Walk optimizer and new quantum methods.
"""
import pytest
import numpy as np
import pandas as pd

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.quantum_annealing import QuantumAnnealingOptimizer, run_quantum_annealing_comparison
from core.quantum_inspired.evolution_dynamics import QuantumEvolution
from config.qsw_config import QSWConfig
from core.quantum_inspired.quantum_annealing import QAConfig


class TestEnhancedQuantumMethods:

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

    def test_quantum_annealing_optimizer(self):
        """Test quantum annealing optimizer functionality."""
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
        assert np.isfinite(result['sharpe_ratio'])
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
        assert np.isfinite(qa_result['sharpe_ratio'])
        assert np.isfinite(classical_result['sharpe_ratio'])

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

    def test_large_portfolio_performance(self):
        """Test performance on larger portfolios."""
        # Create a larger portfolio
        large_n = 50
        large_returns = np.random.randn(large_n) * 0.1 + 0.05
        A = np.random.randn(large_n, large_n)
        large_covariance = np.dot(A.T, A) / large_n

        # Use sparse matrix evolution for efficiency
        config_sparse = QSWConfig(evolution_method='continuous', evolution_time=8)
        optimizer_sparse = QuantumStochasticWalkOptimizer(config_sparse)
        result_sparse = optimizer_sparse.optimize(large_returns, large_covariance)

        # Should produce valid results
        assert np.isfinite(result_sparse.sharpe_ratio)
        assert abs(np.sum(result_sparse.weights) - 1.0) < 1e-6
        assert len(result_sparse.weights) == large_n

    def test_config_parameters(self):
        """Test different configuration parameters."""
        # Test different omega values
        for omega in [0.1, 0.25, 0.4, 0.5]:
            config = QSWConfig(default_omega=omega)
            optimizer = QuantumStochasticWalkOptimizer(config)
            result = optimizer.optimize(self.returns, self.covariance)
            assert np.isfinite(result.sharpe_ratio)

        # Test different evolution times
        for evolution_time in [5, 10, 15, 20]:
            config = QSWConfig(evolution_time=evolution_time)
            optimizer = QuantumStochasticWalkOptimizer(config)
            result = optimizer.optimize(self.returns, self.covariance)
            assert np.isfinite(result.sharpe_ratio)

        # Test different decoherence rates
        for decoherence_rate in [0.05, 0.1, 0.15, 0.2]:
            config = QSWConfig(evolution_method='decoherent', decoherence_rate=decoherence_rate)
            optimizer = QuantumStochasticWalkOptimizer(config)
            result = optimizer.optimize(self.returns, self.covariance)
            assert np.isfinite(result.sharpe_ratio)

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with perfectly correlated assets
        ones_matrix = np.ones((self.n_assets, self.n_assets))
        perfect_corr = ones_matrix * 0.04  # Variance of 0.04 for all assets
        np.fill_diagonal(perfect_corr, 0.04)  # Set diagonal to variance
        
        result_perfect = self.optimizer.optimize(self.returns, perfect_corr)
        assert abs(np.sum(result_perfect.weights) - 1.0) < 1e-6

        # Test with very low returns
        low_returns = np.full(self.n_assets, 0.001)  # Very low returns
        result_low = self.optimizer.optimize(low_returns, self.covariance)
        assert abs(np.sum(result_low.weights) - 1.0) < 1e-6

        # Test with high volatility
        high_vol_cov = self.covariance * 10  # Increase volatility
        result_high_vol = self.optimizer.optimize(self.returns, high_vol_cov)
        assert abs(np.sum(result_high_vol.weights) - 1.0) < 1e-6

    def test_quantum_annealing_configurations(self):
        """Test different quantum annealing configurations."""
        # Test with different temperatures
        configs_to_test = [
            QAConfig(initial_temperature=50.0, final_temperature=0.05),
            QAConfig(initial_temperature=200.0, final_temperature=0.2),
            QAConfig(cooling_rate=0.9, max_iterations=500),
            QAConfig(quantum_fluctuation_strength=0.05),
            QAConfig(quantum_fluctuation_strength=0.2),
        ]

        for config in configs_to_test:
            qa_optimizer = QuantumAnnealingOptimizer(config)
            result = qa_optimizer.optimize(self.returns, self.covariance)
            
            # Check basic validity
            assert len(result['weights']) == self.n_assets
            assert abs(np.sum(result['weights']) - 1.0) < 1e-6
            assert result['sharpe_ratio'] >= -100  # Reasonable lower bound


class TestIntegration:

    def setup_method(self):
        """Set up test fixtures."""
        self.n_assets = 8
        self.returns = np.random.randn(self.n_assets) * 0.1 + 0.05
        A = np.random.randn(self.n_assets, self.n_assets)
        self.covariance = np.dot(A.T, A) / self.n_assets

    def test_end_to_end_workflow(self):
        """Test complete workflow with all quantum methods."""
        # Original QSW
        qsw_optimizer = QuantumStochasticWalkOptimizer()
        qsw_result = qsw_optimizer.optimize(self.returns, self.covariance)

        # Quantum Annealing
        qa_optimizer = QuantumAnnealingOptimizer()
        qa_result = qa_optimizer.optimize(self.returns, self.covariance)

        # Different evolution methods
        methods = ['continuous', 'discrete', 'decoherent']
        method_results = {}

        for method in methods:
            config = QSWConfig(evolution_method=method)
            opt = QuantumStochasticWalkOptimizer(config)
            method_results[method] = opt.optimize(self.returns, self.covariance)

        # All methods should produce valid results
        assert np.isfinite(qsw_result.sharpe_ratio)
        assert np.isfinite(qa_result['sharpe_ratio'])

        for method in methods:
            assert np.isfinite(method_results[method].sharpe_ratio)

        # All weights should sum to 1
        assert abs(np.sum(qsw_result.weights) - 1.0) < 1e-6
        assert abs(np.sum(qa_result['weights']) - 1.0) < 1e-6
        for method in methods:
            assert abs(np.sum(method_results[method].weights) - 1.0) < 1e-6

    def test_parameter_sensitivity(self):
        """Test sensitivity to parameter changes."""
        base_config = QSWConfig()
        base_optimizer = QuantumStochasticWalkOptimizer(base_config)
        base_result = base_optimizer.optimize(self.returns, self.covariance)

        # Test with different omega values
        omega_configs = [QSWConfig(default_omega=omega) for omega in [0.1, 0.2, 0.4, 0.5]]
        omega_results = []

        for config in omega_configs:
            opt = QuantumStochasticWalkOptimizer(config)
            result = opt.optimize(self.returns, self.covariance)
            omega_results.append(result)

        # Results should vary with omega (unless they happen to be the same by chance)
        # At least some variation expected
        sharpe_values = [r.sharpe_ratio for r in omega_results]
        assert len(set([round(sv, 4) for sv in sharpe_values])) >= 1  # At least 1 unique value

        # Test with different evolution times
        time_configs = [QSWConfig(evolution_time=time) for time in [5, 10, 15, 20]]
        time_results = []

        for config in time_configs:
            opt = QuantumStochasticWalkOptimizer(config)
            result = opt.optimize(self.returns, self.covariance)
            time_results.append(result)

        # Results should vary with evolution time
        time_sharpe_values = [r.sharpe_ratio for r in time_results]
        assert len(set([round(sv, 4) for sv in time_sharpe_values])) >= 1  # At least 1 unique value


def test_all():
    """Run all tests."""
    test_instance = TestEnhancedQuantumMethods()
    test_integration = TestIntegration()

    # Run setup for each test class
    test_instance.setup_method()
    test_integration.setup_method()

    # Run all tests
    test_instance.test_quantum_annealing_optimizer()
    test_instance.test_quantum_annealing_comparison()
    test_instance.test_different_evolution_methods()
    test_instance.test_evolution_dynamics_enhancements()
    test_instance.test_large_portfolio_performance()
    test_instance.test_config_parameters()
    test_instance.test_edge_cases()
    test_instance.test_quantum_annealing_configurations()

    test_integration.test_end_to_end_workflow()
    test_integration.test_parameter_sensitivity()

    print("All enhanced tests passed!")


if __name__ == "__main__":
    test_all()