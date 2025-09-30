"""
Unit tests for Quantum Stochastic Walk optimizer.
"""
import pytest
import numpy as np
import pandas as pd

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from config.qsw_config import QSWConfig

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
        assert result.sharpe_ratio >= 0
        assert result.expected_return is not None
        assert result.volatility > 0
    
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