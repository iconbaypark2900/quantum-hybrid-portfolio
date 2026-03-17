"""
Quantum Annealing inspired optimization for portfolio selection.
This module implements quantum annealing concepts adapted for portfolio optimization.
"""
import numpy as np
from typing import Tuple, Dict, Optional
from scipy.optimize import minimize
from dataclasses import dataclass

@dataclass
class QAConfig:
    """Configuration for Quantum Annealing optimizer."""
    # Annealing parameters
    initial_temperature: float = 100.0
    final_temperature: float = 0.1
    cooling_rate: float = 0.95
    max_iterations: int = 1000
    num_samples: int = 100  # For sampling quantum fluctuations
    
    # Problem-specific parameters
    penalty_strength: float = 100.0  # Penalty for constraint violations
    quantum_fluctuation_strength: float = 0.1  # Strength of quantum fluctuations


class QuantumAnnealingOptimizer:
    """
    Quantum Annealing inspired optimizer for portfolio selection.
    
    This approach uses quantum fluctuations to escape local minima
    and find globally optimal portfolio allocations.
    """
    
    def __init__(self, config: Optional[QAConfig] = None):
        self.config = config or QAConfig()
        
    def optimize(self,
                 returns: np.ndarray,
                 covariance: np.ndarray,
                 market_regime: str = 'normal',
                 initial_weights: Optional[np.ndarray] = None) -> Dict:
        """
        Optimize portfolio using quantum annealing approach.
        
        Args:
            returns: Expected returns for each asset
            covariance: Covariance matrix
            market_regime: Current market regime
            initial_weights: Starting weights (for turnover control)
            
        Returns:
            Dictionary with optimization results
        """
        n_assets = len(returns)
        
        # Use quantum-inspired objective function
        result = self._quantum_anneal(
            returns, covariance, n_assets
        )
        
        weights = result['weights']
        
        # Calculate portfolio metrics
        metrics = self._calculate_metrics(weights, returns, covariance)
        
        return {
            'weights': weights,
            'sharpe_ratio': metrics['sharpe_ratio'],
            'expected_return': metrics['expected_return'],
            'volatility': metrics['volatility'],
            'n_active': metrics['n_assets'],
            'objective_value': result['objective_value'],
            'iterations': result['iterations']
        }
    
    def _quantum_anneal(self, returns: np.ndarray, 
                        covariance: np.ndarray, n_assets: int) -> Dict:
        """
        Perform quantum annealing optimization.
        
        This simulates the quantum annealing process by adding quantum fluctuations
        that gradually decrease as the system "cools".
        """
        # Initialize random weights
        current_weights = np.random.dirichlet([1.0] * n_assets)
        current_weights = current_weights / np.sum(current_weights)
        
        current_objective = self._quantum_objective(
            current_weights, returns, covariance
        )
        
        best_weights = current_weights.copy()
        best_objective = current_objective
        
        temperature = self.config.initial_temperature
        iterations = 0
        
        for i in range(self.config.max_iterations):
            # Generate neighbor solution with quantum fluctuations
            neighbor_weights = self._generate_neighbor_with_quantum_fluctuation(
                current_weights
            )
            
            # Enforce constraints
            neighbor_weights = self._enforce_constraints(neighbor_weights)
            
            neighbor_objective = self._quantum_objective(
                neighbor_weights, returns, covariance
            )
            
            # Accept or reject the neighbor
            if neighbor_objective < current_objective:
                # Better solution, accept
                current_weights = neighbor_weights
                current_objective = neighbor_objective
                
                if neighbor_objective < best_objective:
                    best_weights = neighbor_weights
                    best_objective = neighbor_objective
            else:
                # Worse solution, accept with probability
                delta = neighbor_objective - current_objective
                acceptance_prob = np.exp(-delta / temperature)
                
                if np.random.random() < acceptance_prob:
                    current_weights = neighbor_weights
                    current_objective = neighbor_objective
            
            # Cool down
            temperature *= self.config.cooling_rate
            
            # Stop if temperature is low enough
            if temperature < self.config.final_temperature:
                break
                
            iterations = i + 1
        
        return {
            'weights': best_weights,
            'objective_value': best_objective,
            'iterations': iterations
        }
    
    def _quantum_objective(self, weights: np.ndarray, 
                          returns: np.ndarray, covariance: np.ndarray) -> float:
        """
        Quantum-inspired objective function.
        
        This adds quantum fluctuations to the classical objective to help
        escape local minima.
        """
        # Portfolio return
        portfolio_return = np.dot(weights, returns)
        
        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        
        # Sharpe ratio (negative because we minimize)
        if portfolio_variance > 0:
            sharpe = portfolio_return / np.sqrt(portfolio_variance)
        else:
            sharpe = 0
        
        # Add quantum fluctuation term
        quantum_term = self.config.quantum_fluctuation_strength * np.sum(
            np.sin(2 * np.pi * weights)
        )
        
        # Add penalty for constraint violations
        penalty = self.config.penalty_strength * (
            (np.sum(weights) - 1.0)**2 +  # Sum to 1 constraint
            np.sum(np.maximum(0, -weights))**2  # Non-negative weights
        )
        
        # Return negative Sharpe (since we minimize)
        return -(sharpe + quantum_term) + penalty
    
    def _generate_neighbor_with_quantum_fluctuation(self, 
                                                  weights: np.ndarray) -> np.ndarray:
        """
        Generate neighbor solution with quantum fluctuations.
        
        This simulates quantum tunneling effects that allow transitions
        between different local minima.
        """
        n_assets = len(weights)
        
        # Add quantum-inspired perturbation
        quantum_perturbation = self.config.quantum_fluctuation_strength * (
            np.random.normal(0, 0.1, n_assets)
        )
        
        # Also add classical random walk
        classical_perturbation = np.random.normal(0, 0.05, n_assets)
        
        new_weights = weights + quantum_perturbation + classical_perturbation
        
        # Ensure non-negative
        new_weights = np.maximum(new_weights, 0)
        
        # Renormalize
        if np.sum(new_weights) > 0:
            new_weights = new_weights / np.sum(new_weights)
        else:
            # Fallback to uniform if all weights became zero
            new_weights = np.ones(n_assets) / n_assets
            
        return new_weights
    
    def _enforce_constraints(self, weights: np.ndarray) -> np.ndarray:
        """Enforce portfolio constraints."""
        # Ensure non-negative weights
        weights = np.maximum(weights, 0)
        
        # Renormalize to sum to 1
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        else:
            n_assets = len(weights)
            weights = np.ones(n_assets) / n_assets
            
        return weights
    
    def _calculate_metrics(self, weights: np.ndarray, 
                          returns: np.ndarray, covariance: np.ndarray) -> Dict:
        """Calculate portfolio performance metrics."""
        # Expected return
        portfolio_return = np.dot(weights, returns)

        # Volatility
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        # Sharpe ratio (assuming 0 risk-free rate for simplicity)
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0

        # Diversification metrics
        n_assets = np.sum(weights > 1e-6)  # Count assets with meaningful weights
        herfindahl_index = np.sum(weights ** 2)

        return {
            'expected_return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'n_assets': n_assets,
            'herfindahl_index': herfindahl_index,
            'max_weight': np.max(weights),
            'min_weight': np.min(weights[weights > 0]) if np.any(weights > 0) else 0
        }


def run_quantum_annealing_comparison(returns: np.ndarray, 
                                   covariance: np.ndarray) -> Dict:
    """
    Compare quantum annealing with classical optimization.
    """
    qa_optimizer = QuantumAnnealingOptimizer()
    qa_result = qa_optimizer.optimize(returns, covariance)
    
    # Classical optimization for comparison
    from scipy.optimize import minimize
    
    n_assets = len(returns)
    
    def neg_sharpe(weights):
        """Negative Sharpe ratio for minimization."""
        portfolio_return = np.dot(weights, returns)
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        if portfolio_volatility < 1e-10:
            return 1e10  # Invalid portfolio

        return -portfolio_return / portfolio_volatility

    # Constraints: weights sum to 1
    constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}

    # Bounds: all weights between 0 and 1
    bounds = tuple((0, 1) for _ in range(n_assets))

    # Initial guess: equal weight
    x0 = np.ones(n_assets) / n_assets

    # Optimize
    classical_result = minimize(
        neg_sharpe,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    classical_weights = classical_result.x if classical_result.success else x0
    classical_return = np.dot(classical_weights, returns)
    classical_variance = np.dot(classical_weights, np.dot(covariance, classical_weights))
    classical_volatility = np.sqrt(classical_variance)
    classical_sharpe = classical_return / classical_volatility if classical_volatility > 0 else 0
    
    return {
        'quantum_annealing': qa_result,
        'classical': {
            'weights': classical_weights,
            'sharpe_ratio': classical_sharpe,
            'expected_return': classical_return,
            'volatility': classical_volatility,
            'n_active': np.sum(classical_weights > 1e-6)
        }
    }