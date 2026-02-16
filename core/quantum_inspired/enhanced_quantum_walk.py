"""
Enhanced Quantum Stochastic Walk (QSW) implementation for portfolio optimization.
This enhanced version addresses the limitations of the original implementation
and incorporates advanced features for better portfolio optimization.
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
import warnings
from scipy.linalg import expm
import networkx as nx
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm as expm_sparse

from config.qsw_config import QSWConfig
from core.quantum_inspired.graph_builder import FinancialGraphBuilder
from core.quantum_inspired.evolution_dynamics import QuantumEvolution
from core.quantum_inspired.stability_enhancer import StabilityEnhancer

@dataclass
class EnhancedQSWResult:
    """Enhanced result container for QSW optimization."""
    weights: np.ndarray
    sharpe_ratio: float
    expected_return: float
    volatility: float
    turnover: float
    diversification_ratio: float  # Ratio of portfolio volatility to weighted asset volatility
    information_ratio: float  # Excess return over benchmark / tracking error
    max_drawdown: float
    alpha: float  # Excess return over benchmark
    beta: float  # Sensitivity to market movements
    graph_metrics: Dict
    evolution_metrics: Dict
    sector_exposures: Dict  # Exposure to different sectors
    risk_contributions: np.ndarray  # Risk contribution of each asset
    riskMetrics: Dict  # Value at Risk and Conditional VaR

class EnhancedQuantumStochasticWalkOptimizer:
    """
    Enhanced Quantum Stochastic Walk for portfolio optimization.
    
    Key improvements:
    1. Multi-objective optimization balancing return, risk, and diversification
    2. Enhanced Hamiltonian construction with multiple factors
    3. Advanced constraint handling
    4. Regime-aware optimization
    5. Improved stability and convergence
    """

    def __init__(self, config: Optional[QSWConfig] = None, use_optimized: bool = True):
        """
        Initialize enhanced QSW optimizer.

        Args:
            config: Configuration object. Uses defaults if not provided.
            use_optimized: Whether to use optimized implementations
        """
        self.config = config or QSWConfig()
        self.use_optimized = use_optimized

        # Use the original components but with enhanced methods
        self.graph_builder = FinancialGraphBuilder(config)
        self.evolution_engine = QuantumEvolution(config)
        self.stability_enhancer = StabilityEnhancer(config)

        # State tracking
        self.last_weights = None
        self.optimization_history = []
        
        # Benchmark for comparison (equal weight portfolio)
        self.benchmark_weights = None

    def optimize(self,
                 returns: Union[np.ndarray, pd.Series],
                 covariance: Union[np.ndarray, pd.DataFrame],
                 market_regime: str = 'normal',
                 initial_weights: Optional[np.ndarray] = None,
                 sectors: Optional[list] = None,
                 constraints: Optional[Dict] = None) -> EnhancedQSWResult:
        """
        Enhanced optimization method using quantum-inspired walk with multiple objectives.

        Args:
            returns: Expected returns for each asset
            covariance: Covariance matrix
            market_regime: Current market regime ('bull', 'bear', 'volatile', 'normal')
            initial_weights: Starting weights (for turnover control)
            sectors: Sector classification for each asset (optional)
            constraints: Additional constraints dictionary (optional)

        Returns:
            EnhancedQSWResult object containing optimized weights and metrics
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

        # Step 1: Build enhanced financial graph with adaptive parameters
        graph, graph_metrics = self.graph_builder.build_graph(
            returns, covariance, market_regime
        )

        # Add sector information to nodes if provided
        if sectors is not None and len(sectors) == n_assets:
            for i in range(n_assets):
                graph.nodes[i]['sector'] = sectors[i]

        # Step 2: Set evolution parameters based on regime
        omega = self.config.get_omega_for_regime(market_regime)

        # Step 3: Run enhanced quantum-inspired evolution
        raw_weights, evolution_metrics = self._enhanced_evolution(
            graph, returns, covariance, omega, market_regime
        )

        # Step 4: Apply advanced constraints
        constrained_weights = self._apply_enhanced_constraints(
            raw_weights, returns, covariance, sectors, constraints
        )

        # Step 5: Apply stability enhancement to reduce turnover
        if initial_weights is not None:
            stable_weights = self.stability_enhancer.stabilize(
                constrained_weights, initial_weights
            )
            turnover = np.sum(np.abs(stable_weights - initial_weights))
        else:
            stable_weights = constrained_weights
            turnover = 0.0

        # Step 6: Calculate enhanced portfolio metrics
        metrics = self._calculate_enhanced_metrics(
            stable_weights, returns, covariance, self.benchmark_weights
        )

        # Calculate risk metrics
        risk_metrics = self._compute_risk_metrics(returns, stable_weights)

        # Store for next iteration
        self.last_weights = stable_weights.copy()

        # Create enhanced result object
        result = EnhancedQSWResult(
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
            riskMetrics={'var95': risk_metrics['var95'], 'cvar': risk_metrics['cvar']}
        )

        # Track history
        self.optimization_history.append(result)

        return result

    def _enhanced_evolution(self, graph: nx.Graph, returns: np.ndarray, 
                           covariance: np.ndarray, omega: float, 
                           market_regime: str) -> Tuple[np.ndarray, Dict]:
        """
        Enhanced evolution process with multi-objective considerations.
        """
        n_nodes = graph.number_of_nodes()

        # Construct enhanced Hamiltonian
        H = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)

        # Initial state (could be based on previous solution or equal weights)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

        # Time evolution operator - use sparse matrix if large
        if n_nodes > 100:
            H_sparse = csr_matrix(H)
            U = expm_sparse(-1j * H_sparse).toarray()
        else:
            U = expm(-1j * H)

        # Evolved state
        psi_final = U @ psi_0

        # Extract portfolio weights from probability amplitudes
        weights = np.abs(psi_final) ** 2

        # Normalize
        weights = weights / np.sum(weights)

        # Calculate evolution metrics
        metrics = self._calculate_enhanced_evolution_metrics(
            psi_0, psi_final, H, U, weights
        )

        return weights, metrics

    def _construct_enhanced_hamiltonian(self, graph: nx.Graph, omega: float, 
                                       returns: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """
        Enhanced Hamiltonian that captures multiple market factors.
        """
        n = graph.number_of_nodes()
        
        # Original components
        L = nx.laplacian_matrix(graph, weight='weight').toarray()
        
        # Enhanced potential matrix with multiple factors
        V = np.zeros((n, n))
        for i in range(n):
            if graph.has_node(i):
                # Primary return potential
                V[i, i] = graph.nodes[i].get('return_potential', returns[i] if i < len(returns) else 0)
                
                # Risk adjustment
                risk_factor = graph.nodes[i].get('risk', np.sqrt(covariance[i,i]) if i < len(returns) and i < covariance.shape[0] else 1.0)
                V[i, i] = V[i, i] / (1 + risk_factor)
        
        # Sector coupling term (encourage diversification across sectors)
        sector_coupling = self._create_sector_coupling_matrix(graph)
        
        # Market factor exposure (based on beta/correlation to market)
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

    def _apply_enhanced_constraints(self, weights: np.ndarray, returns: np.ndarray, 
                                   covariance: np.ndarray, sectors: Optional[list] = None,
                                   constraints: Optional[Dict] = None) -> np.ndarray:
        """
        Apply enhanced portfolio constraints.
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

    def _apply_sector_constraints(self, weights: np.ndarray, sectors: list) -> np.ndarray:
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

    def _compute_risk_metrics(self, returns: np.ndarray, weights: np.ndarray) -> Dict:
        """Calculate risk metrics including VaR and CVaR."""
        # Calculate portfolio returns
        # If returns is 1D (expected returns), use weighted sum
        # If returns is 2D (historical returns), use dot product
        if len(returns.shape) == 1:
            # This is expected returns vector, not historical returns
            # For risk metrics we need actual returns, so we'll simulate some
            n_sim = 1000  # Number of simulations
            # Generate simulated returns based on expected returns and volatilities
            volatilities = np.sqrt(np.diag(self.last_covariance)) if hasattr(self, 'last_covariance') else np.abs(returns) * 0.5
            simulated_returns = np.random.normal(
                returns - volatilities**2/2,  # Adjusted for log-normal
                volatilities,
                size=(n_sim, len(returns))
            )
            portfolio_returns = np.dot(simulated_returns, weights)
        else:
            # This is historical returns matrix
            portfolio_returns = np.dot(returns, weights)
        
        # Calculate Value at Risk (VaR) at 95% confidence
        var95 = np.percentile(portfolio_returns, 5) if len(portfolio_returns) > 0 else 0.0
        
        # Calculate Conditional Value at Risk (CVaR) / Expected Shortfall
        cvar = np.mean(portfolio_returns[portfolio_returns <= var95]) if len(portfolio_returns) > 0 else 0.0
        
        return {
            'var95': var95,
            'cvar': cvar
        }

    def _calculate_enhanced_evolution_metrics(self, psi_0: np.ndarray,
                                           psi_final: np.ndarray,
                                           H: np.ndarray,
                                           U: np.ndarray,
                                           weights: np.ndarray) -> Dict:
        """Calculate enhanced metrics about the evolution process."""
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
                'graph_density': result.graph_metrics.get('density', 0)
            })

        return pd.DataFrame(history_data)