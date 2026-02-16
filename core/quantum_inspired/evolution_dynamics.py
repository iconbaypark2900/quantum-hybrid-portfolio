"""
Quantum evolution dynamics for portfolio optimization.
Simulates quantum walk on financial graphs.
"""
import numpy as np
import networkx as nx
from scipy.linalg import expm
from typing import Tuple, Dict, Optional
import warnings
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm as expm_sparse

from config.qsw_config import QSWConfig

class QuantumEvolution:
    """
    Implements quantum-inspired evolution dynamics.

    This is where the quantum mathematics provides advantage:
    continuous evolution naturally produces stable, diversified portfolios.
    """

    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize evolution engine."""
        self.config = config or QSWConfig()

    def evolve(self,
              graph: nx.Graph,
              omega: float,
              evolution_time: int) -> Tuple[np.ndarray, Dict]:
        """
        Run quantum-inspired evolution on graph.

        Args:
            graph: Financial graph
            omega: Mixing parameter
            evolution_time: Number of time steps

        Returns:
            Portfolio weights and evolution metrics
        """
        n_nodes = graph.number_of_nodes()

        # Construct Hamiltonian
        H = self._construct_hamiltonian(graph, omega)

        # Initial state (equal superposition)
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
        metrics = self._calculate_evolution_metrics(
            psi_0, psi_final, H, U, weights
        )

        return weights, metrics

    def evolve_discrete_time(self,
                           graph: nx.Graph,
                           omega: float,
                           evolution_steps: int,
                           coin_operator: str = 'hadamard') -> Tuple[np.ndarray, Dict]:
        """
        Run discrete-time quantum walk on graph.
        
        Args:
            graph: Financial graph
            omega: Mixing parameter
            evolution_steps: Number of discrete steps
            coin_operator: Type of coin operator ('hadamard', 'grover', 'fourier')
            
        Returns:
            Portfolio weights and evolution metrics
        """
        n_nodes = graph.number_of_nodes()
        
        # Create extended Hilbert space for position and coin
        # For simplicity, we'll use a position-only approach adapted for DTQW
        H = self._construct_hamiltonian(graph, omega)
        
        # Initial state (equal superposition)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)
        
        # Discrete time evolution
        current_state = psi_0.copy()
        
        for step in range(evolution_steps):
            # Apply Hamiltonian evolution for small time step
            dt = 1.0 / evolution_steps
            U_step = expm(-1j * H * dt)
            current_state = U_step @ current_state
            
            # Normalize to prevent numerical errors
            current_state = current_state / np.linalg.norm(current_state)
        
        # Extract portfolio weights from probability amplitudes
        weights = np.abs(current_state) ** 2
        weights = weights / np.sum(weights)
        
        # Calculate evolution metrics
        metrics = self._calculate_evolution_metrics(
            psi_0, current_state, H, expm(-1j * H), weights
        )
        metrics['evolution_type'] = 'discrete_time'
        
        return weights, metrics

    def evolve_with_decoherence(self,
                               graph: nx.Graph,
                               omega: float,
                               evolution_time: int,
                               decoherence_rate: float = 0.1) -> Tuple[np.ndarray, Dict]:
        """
        Run quantum evolution with controlled decoherence.
        
        Args:
            graph: Financial graph
            omega: Mixing parameter
            evolution_time: Number of time steps
            decoherence_rate: Rate of decoherence (0 to 1)
            
        Returns:
            Portfolio weights and evolution metrics
        """
        n_nodes = graph.number_of_nodes()
        
        # Construct Hamiltonian
        H = self._construct_hamiltonian(graph, omega)
        
        # Initial state (equal superposition)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)
        
        # Time evolution with controlled decoherence
        U = expm(-1j * H * evolution_time)
        
        # Apply decoherence effect
        if decoherence_rate > 0:
            # Mix with identity to simulate decoherence
            mixed_U = (1 - decoherence_rate) * U + decoherence_rate * np.eye(n_nodes)
            psi_final = mixed_U @ psi_0
        else:
            psi_final = U @ psi_0
        
        # Extract portfolio weights from probability amplitudes
        weights = np.abs(psi_final) ** 2
        
        # Normalize
        weights = weights / np.sum(weights)
        
        # Calculate evolution metrics
        metrics = self._calculate_evolution_metrics(
            psi_0, psi_final, H, U, weights
        )
        metrics['decoherence_rate'] = decoherence_rate
        metrics['evolution_type'] = 'with_decoherence'
        
        return weights, metrics

    def _construct_hamiltonian(self, graph: nx.Graph, omega: float) -> np.ndarray:
        """
        Construct quantum Hamiltonian from graph.

        H = -L + ω·V
        where L is graph Laplacian and V is potential (returns).
        """
        n = graph.number_of_nodes()

        # Graph Laplacian (encodes connectivity)
        L = nx.laplacian_matrix(graph, weight='weight').toarray()

        # Node potentials (return-based)
        V = np.zeros((n, n))
        for i in range(n):
            if graph.has_node(i):
                V[i, i] = graph.nodes[i].get('return_potential', 0)
                
        # Add risk-based potential for more sophisticated modeling
        for i in range(n):
            if graph.has_node(i):
                risk_factor = graph.nodes[i].get('risk', 1.0)
                # Adjust potential based on risk profile
                V[i, i] = V[i, i] / (1 + risk_factor)  # Lower potential for higher risk

        # Quantum Hamiltonian
        H = -L + omega * V

        return H

    def _calculate_evolution_metrics(self,
                                    psi_0: np.ndarray,
                                    psi_final: np.ndarray,
                                    H: np.ndarray,
                                    U: np.ndarray,
                                    weights: np.ndarray) -> Dict:
        """Calculate metrics about the evolution process."""
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

        return {
            'state_overlap': overlap,
            'entropy': entropy,
            'effective_n_assets': effective_n,
            'energy': energy,
            'participation_ratio': participation_ratio,
            'max_amplitude': np.max(np.abs(psi_final)),
            'min_amplitude': np.min(np.abs(psi_final)),
            'concentration': concentration,
            'hhi': hhi
        }