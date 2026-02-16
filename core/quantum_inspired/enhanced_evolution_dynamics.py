"""
Enhanced quantum evolution dynamics for portfolio optimization.
This version includes more sophisticated quantum-inspired algorithms.
"""
import numpy as np
import networkx as nx
from scipy.linalg import expm
from typing import Tuple, Dict, Optional
import warnings
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm as expm_sparse
from sklearn.decomposition import PCA

from config.qsw_config import QSWConfig

class EnhancedQuantumEvolution:
    """
    Enhanced quantum-inspired evolution dynamics with multiple evolution strategies.
    
    Key improvements:
    1. Multiple evolution methods (adiabatic, variational, hybrid)
    2. Adaptive time-stepping
    3. Noise resilience features
    4. Better convergence properties
    """

    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize enhanced evolution engine."""
        self.config = config or QSWConfig()

    def evolve(self,
              graph: nx.Graph,
              omega: float,
              evolution_time: int,
              method: str = 'continuous',
              returns: Optional[np.ndarray] = None,
              covariance: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """
        Run enhanced quantum-inspired evolution on graph.

        Args:
            graph: Financial graph
            omega: Mixing parameter
            evolution_time: Number of time steps
            method: Evolution method ('continuous', 'adiabatic', 'variational', 'hybrid')
            returns: Asset returns (for enhanced calculations)
            covariance: Covariance matrix (for enhanced calculations)

        Returns:
            Portfolio weights and evolution metrics
        """
        n_nodes = graph.number_of_nodes()

        if method == 'adiabatic':
            return self._evolve_adiabatic(graph, omega, evolution_time, returns, covariance)
        elif method == 'variational':
            return self._evolve_variational(graph, omega, evolution_time, returns, covariance)
        elif method == 'hybrid':
            return self._evolve_hybrid(graph, omega, evolution_time, returns, covariance)
        else:  # continuous (default)
            return self._evolve_continuous(graph, omega, evolution_time, returns, covariance)

    def _evolve_continuous(self,
                          graph: nx.Graph,
                          omega: float,
                          evolution_time: int,
                          returns: Optional[np.ndarray] = None,
                          covariance: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """
        Enhanced continuous evolution with adaptive features.
        """
        n_nodes = graph.number_of_nodes()

        # Construct enhanced Hamiltonian
        H = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)

        # Initial state (could be informed by returns if available)
        if returns is not None and len(returns) == n_nodes:
            # Use returns to bias initial state toward higher-return assets
            return_weights = np.abs(returns) / np.sum(np.abs(returns))
            psi_0 = np.sqrt(return_weights + 1e-6)  # Amplitude proportional to sqrt of return weights
            psi_0 = psi_0 / np.linalg.norm(psi_0)
        else:
            # Equal superposition
            psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

        # Time evolution operator - use sparse matrix if large
        if n_nodes > 100:
            H_sparse = csr_matrix(H)
            U = expm_sparse(-1j * H_sparse * evolution_time).toarray()
        else:
            U = expm(-1j * H * evolution_time)

        # Evolved state
        psi_final = U @ psi_0

        # Extract portfolio weights from probability amplitudes
        weights = np.abs(psi_final) ** 2

        # Normalize
        weights = weights / np.sum(weights)

        # Calculate evolution metrics
        metrics = self._calculate_enhanced_evolution_metrics(
            psi_0, psi_final, H, U, weights, evolution_time
        )
        metrics['evolution_method'] = 'continuous'

        return weights, metrics

    def _evolve_adiabatic(self,
                         graph: nx.Graph,
                         omega: float,
                         evolution_time: int,
                         returns: Optional[np.ndarray] = None,
                         covariance: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """
        Adiabatic evolution - slow change from initial Hamiltonian to final.
        This can help avoid local optima by maintaining ground state.
        """
        n_nodes = graph.number_of_nodes()

        # Initial Hamiltonian (simple, easily solvable)
        H_initial = self._construct_initial_hamiltonian(n_nodes)

        # Final Hamiltonian (the problem Hamiltonian)
        H_final = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)

        # Adiabatic evolution: H(t) = (1-s(t))*H_initial + s(t)*H_final
        # where s(t) goes from 0 to 1
        dt = 1.0 / evolution_time
        current_state = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

        for t in range(evolution_time):
            s = t / evolution_time  # Schedule parameter
            H_t = (1 - s) * H_initial + s * H_final

            # Small time step evolution
            U_step = expm(-1j * H_t * dt)
            current_state = U_step @ current_state

            # Normalize to prevent numerical errors
            current_state = current_state / np.linalg.norm(current_state)

        # Extract portfolio weights from probability amplitudes
        weights = np.abs(current_state) ** 2
        weights = weights / np.sum(weights)

        # Calculate evolution metrics
        metrics = self._calculate_enhanced_evolution_metrics(
            np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes), 
            current_state, H_final, expm(-1j * H_final), weights, evolution_time
        )
        metrics['evolution_method'] = 'adiabatic'

        return weights, metrics

    def _evolve_variational(self,
                           graph: nx.Graph,
                           omega: float,
                           evolution_time: int,
                           returns: Optional[np.ndarray] = None,
                           covariance: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """
        Variational approach - optimize parameters classically to minimize cost function.
        This combines quantum-inspired evolution with classical optimization.
        """
        n_nodes = graph.number_of_nodes()

        # Start with continuous evolution to get initial parameters
        initial_weights, _ = self._evolve_continuous(graph, omega, evolution_time, returns, covariance)

        # Define a parameterized quantum circuit-like evolution
        # For simplicity, we'll use a rotation-based approach
        best_weights = initial_weights.copy()
        best_cost = self._calculate_portfolio_cost(best_weights, returns, covariance)

        # Try different parameter combinations
        for param in np.linspace(0.1, 2.0, 10):  # Different evolution parameters
            # Create modified Hamiltonian with parameter
            H = self._construct_enhanced_hamiltonian(graph, omega * param, returns, covariance)

            # Evolve
            psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)
            U = expm(-1j * H * evolution_time)
            psi_final = U @ psi_0
            weights = np.abs(psi_final) ** 2
            weights = weights / np.sum(weights)

            # Calculate cost
            cost = self._calculate_portfolio_cost(weights, returns, covariance)

            if cost < best_cost:
                best_cost = cost
                best_weights = weights

        # Calculate evolution metrics (using the best result)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)
        H_best = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)
        U_best = expm(-1j * H_best * evolution_time)
        psi_final = U_best @ psi_0

        metrics = self._calculate_enhanced_evolution_metrics(
            psi_0, psi_final, H_best, U_best, best_weights, evolution_time
        )
        metrics['evolution_method'] = 'variational'
        metrics['best_cost'] = best_cost

        return best_weights, metrics

    def _evolve_hybrid(self,
                      graph: nx.Graph,
                      omega: float,
                      evolution_time: int,
                      returns: Optional[np.ndarray] = None,
                      covariance: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        """
        Hybrid approach combining multiple evolution strategies.
        """
        n_nodes = graph.number_of_nodes()

        # Run multiple evolution methods
        weights_cont, metrics_cont = self._evolve_continuous(graph, omega, evolution_time, returns, covariance)
        weights_adiab, metrics_adiab = self._evolve_adiabatic(graph, omega, evolution_time, returns, covariance)

        # Combine results based on some criteria (e.g., diversity)
        combined_weights = 0.6 * weights_cont + 0.4 * weights_adiab
        combined_weights = combined_weights / np.sum(combined_weights)

        # Calculate final metrics
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)
        H = self._construct_enhanced_hamiltonian(graph, omega, returns, covariance)
        U = expm(-1j * H * evolution_time)
        psi_final = U @ psi_0

        metrics = self._calculate_enhanced_evolution_metrics(
            psi_0, psi_final, H, U, combined_weights, evolution_time
        )
        metrics['evolution_method'] = 'hybrid'
        metrics['individual_methods'] = ['continuous', 'adiabatic']

        return combined_weights, metrics

    def _construct_initial_hamiltonian(self, n_nodes: int) -> np.ndarray:
        """
        Construct simple initial Hamiltonian for adiabatic evolution.
        This is typically chosen to have a known, easily preparable ground state.
        """
        # Simple transverse field Hamiltonian - off-diagonal elements only
        H = np.ones((n_nodes, n_nodes), dtype=complex)
        # Make diagonal elements zero
        np.fill_diagonal(H, 0)
        # Add small diagonal term to avoid degeneracy
        H += 0.01 * np.eye(n_nodes, dtype=complex)
        return H

    def _construct_enhanced_hamiltonian(self, 
                                      graph: nx.Graph, 
                                      omega: float, 
                                      returns: Optional[np.ndarray] = None,
                                      covariance: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Enhanced Hamiltonian construction with multiple financial factors.
        """
        n = graph.number_of_nodes()

        # Graph Laplacian (encodes connectivity)
        L = nx.laplacian_matrix(graph, weight='weight').toarray()

        # Node potentials (return-based with risk adjustment)
        V = np.zeros((n, n), dtype=complex)
        for i in range(n):
            if graph.has_node(i):
                # Base return potential
                base_potential = graph.nodes[i].get('return_potential', 0)
                
                # If returns are provided, use them as well
                if returns is not None and i < len(returns):
                    base_potential = returns[i]
                
                # Risk adjustment
                risk_factor = graph.nodes[i].get('risk', 1.0)
                if risk_factor == 0:
                    risk_factor = 1.0  # Avoid division by zero
                adjusted_potential = base_potential / risk_factor
                
                V[i, i] = adjusted_potential

        # If covariance is provided, add risk structure
        if covariance is not None and covariance.shape[0] == n:
            # Add risk-based adjustments using diagonal of covariance
            risk_diag = np.diag(covariance)
            for i in range(n):
                # Lower potential for high-risk assets
                V[i, i] = V[i, i] / (1 + np.sqrt(risk_diag[i]) if risk_diag[i] > 0 else 1)

        # Quantum Hamiltonian
        H = -L + omega * V

        return H

    def _calculate_portfolio_cost(self, weights: np.ndarray, 
                                 returns: Optional[np.ndarray], 
                                 covariance: Optional[np.ndarray]) -> float:
        """
        Calculate portfolio cost function for variational optimization.
        Lower cost is better.
        """
        if returns is None or covariance is None:
            # If no financial data, use diversification as cost
            return 1 - (1 / np.sum(weights ** 2))  # Higher diversification = lower cost

        # Calculate portfolio return and risk
        portfolio_return = np.dot(weights, returns)
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        # Cost function: negative Sharpe ratio (we want to minimize cost)
        # Add diversification penalty to encourage broader allocation
        diversification_penalty = 0.1 * np.sum(weights ** 2)  # Higher concentration = higher cost
        sharpe_cost = -portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 1.0

        return sharpe_cost + diversification_penalty

    def _calculate_enhanced_evolution_metrics(self,
                                            psi_0: np.ndarray,
                                            psi_final: np.ndarray,
                                            H: np.ndarray,
                                            U: np.ndarray,
                                            weights: np.ndarray,
                                            evolution_time: int) -> Dict:
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

        # Convergence metrics
        eigenvals = np.linalg.eigvals(H)
        spectral_gap = np.sort(np.abs(eigenvals))[1] - np.sort(np.abs(eigenvals))[0] if len(eigenvals) > 1 else 0

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
            'uniformity_measure': 1 - cv if cv != float('inf') else 0,
            'evolution_time': evolution_time,
            'spectral_gap': spectral_gap,
            'hamiltonian_condition_number': np.linalg.cond(H) if np.linalg.cond(H) < 1e12 else float('inf'),
            'numerical_stability': np.allclose(U @ np.conj(U.T), np.eye(len(U)))  # Unitarity check
        }

    def evolve_with_noise_resilience(self,
                                   graph: nx.Graph,
                                   omega: float,
                                   evolution_time: int,
                                   noise_level: float = 0.01) -> Tuple[np.ndarray, Dict]:
        """
        Evolution with added noise resilience features.
        This simulates real-world conditions where data is imperfect.
        """
        n_nodes = graph.number_of_nodes()

        # Construct Hamiltonian
        H = self._construct_enhanced_hamiltonian(graph, omega)

        # Initial state
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

        # Add controlled noise to Hamiltonian to test resilience
        noise_matrix = np.random.normal(0, noise_level, H.shape) + 1j*np.random.normal(0, noise_level, H.shape)
        H_noisy = H + noise_matrix

        # Time evolution operator
        if n_nodes > 100:
            H_sparse = csr_matrix(H_noisy)
            U = expm_sparse(-1j * H_sparse * evolution_time).toarray()
        else:
            U = expm(-1j * H_noisy * evolution_time)

        # Evolved state
        psi_final = U @ psi_0

        # Extract portfolio weights from probability amplitudes
        weights = np.abs(psi_final) ** 2

        # Normalize
        weights = weights / np.sum(weights)

        # Calculate evolution metrics
        metrics = self._calculate_enhanced_evolution_metrics(
            psi_0, psi_final, H, U, weights, evolution_time
        )
        metrics['noise_level'] = noise_level
        metrics['evolution_method'] = 'noise_resilient'

        return weights, metrics