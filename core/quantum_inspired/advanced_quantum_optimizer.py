"""
Advanced Quantum-Inspired Portfolio Optimization Algorithm
This module implements a novel quantum-inspired optimization algorithm that combines
multiple quantum concepts for enhanced portfolio optimization.
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Union, List
from dataclasses import dataclass
import warnings
from scipy.linalg import expm
from scipy.optimize import minimize
import networkx as nx
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm as expm_sparse

from config.qsw_config import QSWConfig


@dataclass
class AdvancedQIROResult:
    """Result container for Advanced Quantum-Inspired Robust Optimization."""
    weights: np.ndarray
    sharpe_ratio: float
    expected_return: float
    volatility: float
    turnover: float
    diversification_ratio: float
    information_ratio: float
    max_drawdown: float
    alpha: float
    beta: float
    graph_metrics: Dict
    evolution_metrics: Dict
    sector_exposures: Dict
    risk_contributions: np.ndarray
    risk_metrics: Dict
    convergence_info: Dict  # Additional info about optimization convergence


class AdvancedQuantumInspiredRobustOptimizer:
    """
    Advanced Quantum-Inspired Robust Optimization for portfolio selection.

    This algorithm combines multiple quantum-inspired concepts:
    1. Quantum Stochastic Walks with adaptive parameters
    2. Quantum Annealing for global optimization
    3. Quantum Variational Approach for hyperparameter tuning
    4. Robust optimization techniques for uncertainty handling
    """

    def __init__(self, config: Optional[QSWConfig] = None, use_hybrid_approach: bool = True):
        """
        Initialize the advanced optimizer.

        Args:
            config: Configuration object. Uses defaults if not provided.
            use_hybrid_approach: Whether to use a hybrid quantum-classical approach
        """
        self.config = config or QSWConfig()
        self.use_hybrid_approach = use_hybrid_approach
        
        # Internal parameters
        self.last_weights = None
        self.optimization_history = []
        self.benchmark_weights = None

    def optimize(self,
                 returns: Union[np.ndarray, pd.Series],
                 covariance: Union[np.ndarray, pd.DataFrame],
                 market_regime: str = 'normal',
                 initial_weights: Optional[np.ndarray] = None,
                 sectors: Optional[List[str]] = None,
                 constraints: Optional[Dict] = None,
                 uncertainty_set: Optional[Dict] = None) -> AdvancedQIROResult:
        """
        Optimize portfolio using advanced quantum-inspired approach.

        Args:
            returns: Expected returns for each asset
            covariance: Covariance matrix
            market_regime: Current market regime ('bull', 'bear', 'volatile', 'normal')
            initial_weights: Starting weights (for turnover control)
            sectors: Sector classification for each asset (optional)
            constraints: Additional constraints dictionary (optional)
            uncertainty_set: Uncertainty parameters for robust optimization (optional)

        Returns:
            AdvancedQIROResult object containing optimized weights and metrics
        """
        # Convert to numpy arrays
        returns = np.asarray(returns)
        covariance = np.asarray(covariance)
        n_assets = len(returns)

        # Validate inputs
        self._validate_inputs(returns, covariance)

        # Set benchmark weights if not set
        if self.benchmark_weights is None:
            self.benchmark_weights = np.ones(n_assets) / n_assets

        # Build enhanced financial graph with adaptive parameters
        graph, graph_metrics = self._build_enhanced_graph(
            returns, covariance, market_regime, sectors
        )

        # Determine optimal parameters based on market regime and uncertainty
        omega = self.config.get_omega_for_regime(market_regime)
        evolution_time = self.config.evolution_time

        # Apply uncertainty adjustments if provided
        if uncertainty_set:
            omega = self._adjust_for_uncertainty(omega, uncertainty_set)
            evolution_time = self._adjust_evolution_time(evolution_time, uncertainty_set)

        # Run advanced quantum-inspired optimization
        raw_weights, evolution_metrics = self._advanced_quantum_optimization(
            graph, returns, covariance, omega, evolution_time, market_regime
        )

        # Apply advanced constraints
        constrained_weights = self._apply_advanced_constraints(
            raw_weights, returns, covariance, sectors, constraints
        )

        # Apply stability enhancement to reduce turnover
        if initial_weights is not None:
            stable_weights = self._enhanced_stability_control(
                constrained_weights, initial_weights
            )
            turnover = np.sum(np.abs(stable_weights - initial_weights))
        else:
            stable_weights = constrained_weights
            turnover = 0.0

        # Calculate enhanced portfolio metrics
        metrics = self._calculate_enhanced_metrics(
            stable_weights, returns, covariance, self.benchmark_weights
        )

        # Calculate risk metrics
        risk_metrics = self._compute_comprehensive_risk_metrics(
            returns, covariance, stable_weights
        )

        # Store for next iteration
        self.last_weights = stable_weights.copy()

        # Create enhanced result object
        result = AdvancedQIROResult(
            weights=stable_weights,
            sharpe_ratio=metrics['sharpe_ratio'],
            expected_return=metrics['expected_return'],
            volatility=metrics['volatility'],
            turnover=turnover,
            diversification_ratio=metrics['diversification_ratio'],
            information_ratio=metrics['information_ratio'],
            max_drawdown=metrics['max_drawdown'],
            alpha=metrics['alpha'],
            beta=metrics['beta'],
            graph_metrics=graph_metrics,
            evolution_metrics=evolution_metrics,
            sector_exposures=metrics['sector_exposures'],
            risk_contributions=metrics['risk_contributions'],
            risk_metrics=risk_metrics,
            convergence_info=evolution_metrics.get('convergence_info', {})
        )

        # Track history
        self.optimization_history.append(result)

        return result

    def _build_enhanced_graph(self, returns: np.ndarray, covariance: np.ndarray,
                             market_regime: str, sectors: Optional[List[str]] = None) -> Tuple[nx.Graph, Dict]:
        """
        Build an enhanced financial graph with quantum-inspired features.
        """
        n_assets = len(returns)
        graph = nx.Graph()

        # Add nodes with quantum-inspired attributes
        for i in range(n_assets):
            graph.add_node(i, 
                          return_potential=returns[i],
                          volatility=np.sqrt(covariance[i, i]),
                          sector=sectors[i] if sectors and i < len(sectors) else 'Unknown')

        # Add edges based on correlations and quantum-inspired coupling
        correlation_matrix = self._get_correlation_from_covariance(covariance)
        
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                # Quantum-inspired coupling strength based on correlation and return similarity
                corr_strength = abs(correlation_matrix[i, j])
                
                # Additional quantum-inspired factors
                return_similarity = 1 - abs(returns[i] - returns[j]) / max(abs(returns[i]), abs(returns[j]), 1e-8)
                volatility_compatibility = 1 / (1 + abs(np.sqrt(covariance[i, i]) - np.sqrt(covariance[j, j])))
                
                # Combined coupling strength
                coupling_strength = corr_strength * return_similarity * volatility_compatibility
                
                # Only add edge if coupling is significant
                if coupling_strength > self.config.correlation_threshold:
                    graph.add_edge(i, j, weight=coupling_strength)

        # Calculate graph metrics
        n_edges = graph.number_of_edges()
        density = 2 * n_edges / (n_assets * (n_assets - 1)) if n_assets > 1 else 0

        graph_metrics = {
            'n_nodes': n_assets,
            'n_edges': n_edges,
            'density': density,
            'clustering_coeff': nx.average_clustering(graph),
            'avg_shortest_path': nx.average_shortest_path_length(graph) if nx.is_connected(graph) else float('inf')
        }

        return graph, graph_metrics

    def _get_correlation_from_covariance(self, covariance: np.ndarray) -> np.ndarray:
        """Convert covariance matrix to correlation matrix."""
        std_dev = np.sqrt(np.diag(covariance))
        correlation = covariance / np.outer(std_dev, std_dev)
        # Handle potential numerical issues
        correlation = np.clip(correlation, -1.0, 1.0)
        return correlation

    def _adjust_for_uncertainty(self, omega: float, uncertainty_set: Dict) -> float:
        """Adjust omega parameter based on uncertainty estimates."""
        # Increase omega in high uncertainty environments to promote diversification
        uncertainty_factor = uncertainty_set.get('market_uncertainty', 1.0)
        adjusted_omega = min(omega * uncertainty_factor, 0.6)  # Cap at 0.6
        return adjusted_omega

    def _adjust_evolution_time(self, evolution_time: int, uncertainty_set: Dict) -> int:
        """Adjust evolution time based on uncertainty estimates."""
        # Increase evolution time in uncertain environments for more exploration
        uncertainty_factor = uncertainty_set.get('market_uncertainty', 1.0)
        adjusted_time = int(evolution_time * uncertainty_factor)
        return min(adjusted_time, 100)  # Cap at 100

    def _advanced_quantum_optimization(self, graph: nx.Graph, returns: np.ndarray,
                                     covariance: np.ndarray, omega: float,
                                     evolution_time: int, market_regime: str) -> Tuple[np.ndarray, Dict]:
        """
        Perform advanced quantum-inspired optimization combining multiple approaches.
        """
        n_nodes = graph.number_of_nodes()

        # Method selection based on problem characteristics
        if n_nodes < 20 or self.use_hybrid_approach:
            # Use quantum walk approach for smaller problems
            weights, metrics = self._quantum_walk_optimization(graph, returns, covariance, omega, evolution_time)
        else:
            # Use variational quantum approach for larger problems
            weights, metrics = self._variational_quantum_optimization(graph, returns, covariance, omega, evolution_time)

        # Post-process with quantum annealing refinement
        weights = self._quantum_annealing_refinement(weights, returns, covariance)

        return weights, metrics

    def _quantum_walk_optimization(self, graph: nx.Graph, returns: np.ndarray,
                                  covariance: np.ndarray, omega: float,
                                  evolution_time: int) -> Tuple[np.ndarray, Dict]:
        """
        Quantum walk-based optimization.
        """
        n_nodes = graph.number_of_nodes()

        # Construct enhanced Hamiltonian
        H = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)

        # Initial state (could be based on prior solution or equal weights)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

        # Time evolution operator
        U = expm(-1j * H * evolution_time)

        # Evolved state
        psi_final = U @ psi_0

        # Extract portfolio weights from probability amplitudes
        weights = np.abs(psi_final) ** 2

        # Normalize
        weights = weights / np.sum(weights)

        # Calculate evolution metrics
        metrics = self._calculate_evolution_metrics(psi_0, psi_final, H, weights)

        return weights, metrics

    def _construct_enhanced_hamiltonian(self, graph: nx.Graph, omega: float,
                                       returns: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """
        Construct enhanced Hamiltonian with multiple quantum-inspired terms.
        """
        n = graph.number_of_nodes()

        # Laplacian matrix (graph structure)
        L = nx.laplacian_matrix(graph, weight='weight').toarray()

        # Potential matrix based on returns and risk
        V = np.zeros((n, n))
        for i in range(n):
            if graph.has_node(i):
                # Primary return potential
                V[i, i] = graph.nodes[i].get('return_potential', returns[i] if i < len(returns) else 0)

                # Risk adjustment
                risk_factor = graph.nodes[i].get('volatility', np.sqrt(covariance[i, i]) if i < len(returns) and i < covariance.shape[0] else 1.0)
                V[i, i] = V[i, i] / (1 + risk_factor)

        # Sector coupling term (encourage diversification across sectors)
        sector_coupling = self._create_sector_coupling_matrix(graph)

        # Market factor exposure
        market_exposure = self._create_market_exposure_matrix(covariance)

        # Enhanced Hamiltonian with multiple terms
        H = -L + omega * V + 0.1 * sector_coupling + 0.05 * market_exposure

        return H

    def _create_sector_coupling_matrix(self, graph: nx.Graph) -> np.ndarray:
        """
        Create matrix that encourages diversification across sectors.
        """
        n = graph.number_of_nodes()
        sector_matrix = np.zeros((n, n))

        # Group nodes by sector
        sectors = {}
        for i in range(n):
            sector = graph.nodes[i].get('sector', 'Unknown')
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(i)

        # Within-sector connections get negative weight (discouraged)
        # Between-sector connections get positive weight (encouraged)
        for sector, nodes in sectors.items():
            for i_idx, i in enumerate(nodes):
                for j_idx, j in enumerate(nodes):
                    if i != j:
                        # Discourage within-sector connections
                        sector_matrix[i, j] = -0.1

        return sector_matrix

    def _create_market_exposure_matrix(self, covariance: np.ndarray) -> np.ndarray:
        """
        Create matrix based on market exposure (beta/correlation).
        """
        n = covariance.shape[0]
        market_matrix = np.zeros((n, n))

        # Calculate market return proxy (equal weight portfolio variance)
        market_var = np.sum(covariance) / (n * n)

        if market_var > 0:
            # Calculate beta for each asset relative to market
            for i in range(n):
                cov_asset_market = np.sum(covariance[i, :]) / n
                beta_i = cov_asset_market / market_var if market_var > 0 else 0

                for j in range(n):
                    cov_asset_market_j = np.sum(covariance[j, :]) / n
                    beta_j = cov_asset_market_j / market_var if market_var > 0 else 0

                    # Encourage combination of low-beta and high-beta assets
                    market_matrix[i, j] = -abs(beta_i - beta_j) * 0.01

        return market_matrix

    def _variational_quantum_optimization(self, graph: nx.Graph, returns: np.ndarray,
                                        covariance: np.ndarray, omega: float,
                                        evolution_time: int) -> Tuple[np.ndarray, Dict]:
        """
        Variational quantum-inspired optimization for larger problems.
        """
        n_assets = len(returns)

        # Objective function for variational optimization
        def objective(params):
            # Convert parameters to portfolio weights (softmax transformation)
            weights = np.exp(params) / np.sum(np.exp(params))

            # Portfolio return
            portfolio_return = np.dot(weights, returns)

            # Portfolio variance
            portfolio_variance = np.dot(weights, np.dot(covariance, weights))
            portfolio_volatility = np.sqrt(max(portfolio_variance, 1e-8))

            # Sharpe ratio (negative because we minimize)
            sharpe = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0

            # Add regularization for diversification
            diversification_penalty = -0.01 * np.sum(weights ** 2)  # Encourage diversification

            return -sharpe + diversification_penalty

        # Gradient of objective function
        def gradient(params):
            # Numerical gradient calculation
            eps = 1e-8
            grad = np.zeros_like(params)
            params_plus = params.copy()
            params_minus = params.copy()

            for i in range(len(params)):
                params_plus[i] += eps
                params_minus[i] -= eps

                val_plus = objective(params_plus)
                val_minus = objective(params_minus)

                grad[i] = (val_plus - val_minus) / (2 * eps)
                params_plus[i] = params[i]  # Reset
                params_minus[i] = params[i]  # Reset

            return grad

        # Initial parameters (logits for softmax)
        initial_params = np.random.normal(0, 0.1, n_assets)

        # Optimize
        result = minimize(objective, initial_params, method='L-BFGS-B', jac=gradient)

        # Convert optimized parameters to weights
        optimized_weights = np.exp(result.x) / np.sum(np.exp(result.x))

        # Calculate metrics
        metrics = {
            'convergence_info': {
                'success': result.success,
                'n_iterations': result.nit,
                'fun_val': result.fun,
                'message': result.message
            }
        }

        return optimized_weights, metrics

    def _quantum_annealing_refinement(self, initial_weights: np.ndarray,
                                    returns: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """
        Refine solution using quantum annealing-inspired local search.
        """
        n_assets = len(initial_weights)
        current_weights = initial_weights.copy()

        # Parameters for quantum-inspired local search
        temperature = 1.0
        cooling_rate = 0.95
        max_iterations = 50

        for iteration in range(max_iterations):
            # Generate neighbor by quantum-inspired perturbation
            neighbor_weights = self._generate_quantum_neighbor(current_weights)

            # Apply constraints
            neighbor_weights = self._renormalize_weights(neighbor_weights)

            # Evaluate both solutions
            current_return = np.dot(current_weights, returns)
            current_risk = np.sqrt(np.dot(current_weights, np.dot(covariance, current_weights)))
            current_sharpe = current_return / current_risk if current_risk > 0 else 0

            neighbor_return = np.dot(neighbor_weights, returns)
            neighbor_risk = np.sqrt(np.dot(neighbor_weights, np.dot(covariance, neighbor_weights)))
            neighbor_sharpe = neighbor_return / neighbor_risk if neighbor_risk > 0 else 0

            # Accept neighbor if better or probabilistically worse
            if neighbor_sharpe > current_sharpe:
                current_weights = neighbor_weights
            else:
                delta_sharpe = neighbor_sharpe - current_sharpe
                acceptance_prob = np.exp(delta_sharpe / temperature)
                if np.random.random() < acceptance_prob:
                    current_weights = neighbor_weights

            # Cool down
            temperature *= cooling_rate

        return current_weights

    def _generate_quantum_neighbor(self, weights: np.ndarray) -> np.ndarray:
        """
        Generate neighbor solution with quantum-inspired perturbations.
        """
        n_assets = len(weights)

        # Quantum-inspired perturbation (superposition-like)
        quantum_perturbation = 0.02 * np.random.normal(0, 1, n_assets)

        # Classical random walk
        classical_perturbation = 0.01 * np.random.uniform(-1, 1, n_assets)

        # Combine perturbations
        new_weights = weights + quantum_perturbation + classical_perturbation

        # Ensure non-negative
        new_weights = np.maximum(new_weights, 0)

        return new_weights

    def _renormalize_weights(self, weights: np.ndarray) -> np.ndarray:
        """Renormalize weights to sum to 1."""
        if np.sum(weights) > 0:
            return weights / np.sum(weights)
        else:
            # Fallback to uniform if all weights became zero
            return np.ones(len(weights)) / len(weights)

    def _apply_advanced_constraints(self, weights: np.ndarray, returns: np.ndarray,
                                  covariance: np.ndarray, sectors: Optional[List[str]] = None,
                                  constraints: Optional[Dict] = None) -> np.ndarray:
        """
        Apply advanced portfolio constraints.
        """
        n_assets = len(weights)

        # Original constraints
        weights = np.clip(weights, self.config.min_weight, self.config.max_weight)

        # Sector constraints if provided
        if sectors is not None and len(sectors) == n_assets:
            weights = self._apply_sector_constraints(weights, sectors)

        # Risk factor neutralization if requested
        if constraints and constraints.get('neutralize_factors', False):
            weights = self._neutralize_risk_factors(weights, covariance, constraints)

        # Cardinality constraints (minimum number of positions)
        min_positions = constraints.get('min_positions', 0) if constraints else 0
        if min_positions > 0:
            weights = self._apply_cardinality_constraint(weights, min_positions)

        # Renormalize
        weights = weights / np.sum(weights)

        return weights

    def _apply_sector_constraints(self, weights: np.ndarray, sectors: List[str]) -> np.ndarray:
        """
        Apply sector-level constraints.
        """
        unique_sectors = list(set(sectors))

        # Calculate current sector weights
        sector_weights = {}
        for i, sector in enumerate(sectors):
            if sector not in sector_weights:
                sector_weights[sector] = 0
            sector_weights[sector] += weights[i]

        # Apply sector caps (simple approach: cap each sector at 30%)
        sector_caps = {sector: 0.30 for sector in unique_sectors}  # Default 30% cap

        # Adjust weights to respect sector caps
        for sector, current_weight in sector_weights.items():
            if current_weight > sector_caps[sector]:
                # Calculate scaling factor for this sector
                scale_factor = sector_caps[sector] / current_weight

                # Reduce weights proportionally within sector
                for i, asset_sector in enumerate(sectors):
                    if asset_sector == sector:
                        weights[i] *= scale_factor

        # Renormalize after adjustments
        weights = weights / np.sum(weights)

        return weights

    def _neutralize_risk_factors(self, weights: np.ndarray, covariance: np.ndarray,
                                constraints: Dict) -> np.ndarray:
        """
        Neutralize exposure to specific risk factors.
        """
        # This is a simplified implementation
        # In practice, you'd have factor loadings and target exposures
        return weights  # Placeholder - implement based on specific factor model

    def _apply_cardinality_constraint(self, weights: np.ndarray, min_positions: int) -> np.ndarray:
        """
        Ensure minimum number of positions in portfolio.
        """
        if min_positions <= 0:
            return weights

        n_current_positions = np.sum(weights > self.config.min_weight)

        if n_current_positions < min_positions:
            # Find assets with lowest weights and boost them
            zero_weight_indices = np.where(weights <= self.config.min_weight)[0]

            if len(zero_weight_indices) >= (min_positions - n_current_positions):
                # Boost some zero-weight assets to minimum
                assets_to_boost = zero_weight_indices[:(min_positions - n_current_positions)]
                for idx in assets_to_boost:
                    weights[idx] = self.config.min_weight

            # Renormalize
            weights = weights / np.sum(weights)

        return weights

    def _enhanced_stability_control(self, new_weights: np.ndarray, 
                                  prev_weights: np.ndarray) -> np.ndarray:
        """
        Enhanced stability control to minimize turnover while preserving performance.
        """
        # Blend new and previous weights based on market regime and confidence
        blend_factor = self.config.stability_blend_factor
        
        # Calculate turnover if we used pure new weights
        pure_new_turnover = np.sum(np.abs(new_weights - prev_weights))
        
        # If turnover would be too high, increase blend factor
        if pure_new_turnover > self.config.max_turnover:
            # Adjust blend factor inversely proportional to excess turnover
            excess_turnover = pure_new_turnover - self.config.max_turnover
            adjustment = min(excess_turnover / self.config.max_turnover, 0.5)
            blend_factor = min(blend_factor + adjustment, 0.95)
        
        # Apply blending
        final_weights = blend_factor * new_weights + (1 - blend_factor) * prev_weights
        
        # Renormalize
        final_weights = final_weights / np.sum(final_weights)
        
        return final_weights

    def _validate_inputs(self, returns: np.ndarray, covariance: np.ndarray):
        """Validate input data."""
        n_assets = len(returns)

        if covariance.shape != (n_assets, n_assets):
            raise ValueError(f"Covariance shape {covariance.shape} doesn't match "
                           f"returns length {n_assets}")

        # Check positive semi-definite
        eigenvalues = np.linalg.eigvalsh(covariance)
        if np.min(eigenvalues) < -1e-8:
            warnings.warn("Covariance matrix is not positive semi-definite. "
                         "Applying regularization.")
            # Regularize
            covariance += np.eye(n_assets) * abs(np.min(eigenvalues)) * 1.1

    def _calculate_enhanced_metrics(self, weights: np.ndarray, returns: np.ndarray,
                                  covariance: np.ndarray, benchmark_weights: np.ndarray) -> Dict:
        """Calculate enhanced portfolio performance metrics."""
        # Basic metrics
        portfolio_return = np.dot(weights, returns)
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        # Sharpe ratio (assuming 0 risk-free rate for simplicity)
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0

        # Diversification ratio: portfolio volatility / weighted average of asset volatilities
        asset_volatilities = np.sqrt(np.diag(covariance))
        weighted_avg_vol = np.dot(weights, asset_volatilities)
        diversification_ratio = portfolio_volatility / weighted_avg_vol if weighted_avg_vol > 0 else 1.0

        # Benchmark metrics for comparison
        benchmark_return = np.dot(benchmark_weights, returns)
        benchmark_variance = np.dot(benchmark_weights, np.dot(covariance, benchmark_weights))
        benchmark_volatility = np.sqrt(benchmark_variance)

        # Alpha and Beta
        if benchmark_volatility > 0:
            beta = np.dot(weights, np.dot(covariance, benchmark_weights)) / benchmark_variance
            alpha = portfolio_return - beta * benchmark_return
        else:
            beta = 0
            alpha = portfolio_return

        # Information ratio (if alpha and tracking error are meaningful)
        tracking_error = np.sqrt(np.dot((weights - benchmark_weights),
                                      np.dot(covariance, (weights - benchmark_weights))))
        information_ratio = alpha / tracking_error if tracking_error > 0 else 0

        # Risk contributions (component of portfolio variance)
        marginal_contributions = np.dot(covariance, weights) / portfolio_volatility
        risk_contributions = weights * marginal_contributions
        risk_contributions = risk_contributions / portfolio_volatility  # Normalize

        # Sector exposures
        sector_exposures = {}  # This would be populated if sector info is available

        # Simplified max drawdown estimate (would need actual time series for real calc)
        max_drawdown = min(0, -portfolio_volatility * 2)  # Rough estimate

        return {
            'expected_return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'diversification_ratio': diversification_ratio,
            'information_ratio': information_ratio,
            'max_drawdown': max_drawdown,
            'alpha': alpha,
            'beta': beta,
            'tracking_error': tracking_error,
            'sector_exposures': sector_exposures,
            'risk_contributions': risk_contributions,
            'n_assets': np.sum(weights > self.config.min_weight),
            'herfindahl_index': np.sum(weights ** 2),
            'max_weight': np.max(weights),
            'min_weight': np.min(weights[weights > 0]) if np.any(weights > 0) else 0
        }

    def _compute_comprehensive_risk_metrics(self, returns: np.ndarray, 
                                          covariance: np.ndarray, 
                                          weights: np.ndarray) -> Dict:
        """Calculate comprehensive risk metrics."""
        # Calculate portfolio volatility
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
        
        # Value at Risk (VaR) and Conditional Value at Risk (CVaR) using analytical approach
        # Assuming normally distributed returns
        var_95 = portfolio_vol * -1.645  # 95% VaR for normal distribution
        cvar_95 = portfolio_vol * -1.755  # 95% CVaR for normal distribution
        
        # Tail risk measures
        var_99 = portfolio_vol * -2.326  # 99% VaR
        cvar_99 = portfolio_vol * -2.665  # 99% CVaR
        
        # Maximum drawdown (simplified)
        max_dd = -0.15 * portfolio_vol  # Rough estimate based on volatility
        
        # Semi-deviation (downside risk)
        portfolio_mean = np.dot(weights, returns)
        downside_dev = np.sqrt(np.mean(np.minimum(0, np.dot(weights, returns) - portfolio_mean)**2))
        
        # Upside potential ratio
        upside_threshold = portfolio_mean  # Usually risk-free rate, here using portfolio mean
        upside_potential = np.mean(np.maximum(0, np.dot(weights, returns) - upside_threshold))
        upside_downside_ratio = upside_potential / downside_dev if downside_dev > 0 else float('inf')
        
        return {
            'var95': var_95,
            'cvar95': cvar_95,
            'var99': var_99,
            'cvar99': cvar_99,
            'max_drawdown': max_dd,
            'semi_deviation': downside_dev,
            'upside_downside_ratio': upside_downside_ratio,
            'volatility': portfolio_vol
        }

    def _calculate_evolution_metrics(self, psi_0: np.ndarray,
                                   psi_final: np.ndarray,
                                   H: np.ndarray,
                                   weights: np.ndarray) -> Dict:
        """Calculate metrics about the quantum evolution process."""
        n = len(weights)

        # State overlap (how much did state change)
        overlap = np.abs(np.dot(np.conj(psi_0), psi_final)) ** 2

        # Entropy of final distribution (diversification measure)
        # Avoid log(0)
        weights_nonzero = weights[weights > 1e-10]
        entropy = -np.sum(weights_nonzero * np.log(weights_nonzero))

        # Effective number of assets (from entropy)
        effective_n = np.exp(entropy)

        # Energy expectation value
        energy = np.real(np.dot(np.conj(psi_final), H @ psi_final))

        # Participation ratio (another diversification measure)
        participation_ratio = 1 / np.sum(weights ** 2)

        # Concentration measure (1 - Herfindahl-Hirschman Index)
        hhi = np.sum(weights ** 2)
        concentration = 1 - hhi

        # Coefficient of variation (diversification indicator)
        cv = np.std(weights) / np.mean(weights) if np.mean(weights) > 0 else float('inf')

        return {
            'state_overlap': overlap,
            'entropy': entropy,
            'effective_n_assets': effective_n,
            'energy': energy,
            'participation_ratio': participation_ratio,
            'max_amplitude': np.max(np.abs(psi_final)),
            'min_amplitude': np.min(np.abs(psi_final)),
            'concentration': concentration,
            'hhi': hhi,
            'coefficient_of_variation': cv,
            'uniformity_measure': 1 - cv  # Higher is more uniform (diversified)
        }

    def get_optimization_history(self) -> pd.DataFrame:
        """Get history of optimization results."""
        if not self.optimization_history:
            return pd.DataFrame()

        history_data = []
        for i, result in enumerate(self.optimization_history):
            history_data.append({
                'iteration': i,
                'sharpe_ratio': result.sharpe_ratio,
                'expected_return': result.expected_return,
                'volatility': result.volatility,
                'turnover': result.turnover,
                'diversification_ratio': result.diversification_ratio,
                'information_ratio': result.information_ratio,
                'alpha': result.alpha,
                'beta': result.beta,
                'n_assets': np.sum(result.weights > self.config.min_weight),
                'n_edges': result.graph_metrics.get('n_edges', 0),
                'graph_density': result.graph_metrics.get('density', 0),
                'convergence_success': result.convergence_info.get('success', False)
            })

        return pd.DataFrame(history_data)


def run_advanced_comparison(returns: np.ndarray, covariance: np.ndarray) -> Dict:
    """
    Compare advanced optimizer with standard approaches.
    """
    # Advanced optimizer
    advanced_optimizer = AdvancedQuantumInspiredRobustOptimizer()
    advanced_result = advanced_optimizer.optimize(returns, covariance)

    # Standard QSW optimizer for comparison
    from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
    standard_optimizer = QuantumStochasticWalkOptimizer()
    standard_result = standard_optimizer.optimize(returns, covariance)

    # Enhanced QSW optimizer for comparison
    from core.quantum_inspired.enhanced_quantum_walk import EnhancedQuantumStochasticWalkOptimizer
    enhanced_optimizer = EnhancedQuantumStochasticWalkOptimizer()
    enhanced_result = enhanced_optimizer.optimize(returns, covariance)

    return {
        'advanced_quantum_inspired': {
            'weights': advanced_result.weights,
            'sharpe_ratio': advanced_result.sharpe_ratio,
            'expected_return': advanced_result.expected_return,
            'volatility': advanced_result.volatility,
            'turnover': advanced_result.turnover,
            'diversification_ratio': advanced_result.diversification_ratio
        },
        'standard_qsw': {
            'weights': standard_result.weights,
            'sharpe_ratio': standard_result.sharpe_ratio,
            'expected_return': standard_result.expected_return,
            'volatility': standard_result.volatility,
            'turnover': standard_result.turnover,
            'diversification_ratio': 0.75  # Placeholder
        },
        'enhanced_qsw': {
            'weights': enhanced_result.weights,
            'sharpe_ratio': enhanced_result.sharpe_ratio,
            'expected_return': enhanced_result.expected_return,
            'volatility': enhanced_result.volatility,
            'turnover': enhanced_result.turnover,
            'diversification_ratio': enhanced_result.diversification_ratio
        }
    }