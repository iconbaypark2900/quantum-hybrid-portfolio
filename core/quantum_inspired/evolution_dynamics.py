"""
Quantum evolution dynamics for portfolio optimization.
Simulates quantum walk on financial graphs.
"""
import numpy as np
import networkx as nx
from scipy.linalg import expm
from typing import Tuple, Dict, Optional
import warnings

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
        
        # Time evolution operator
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
        
        return {
            'state_overlap': overlap,
            'entropy': entropy,
            'effective_n_assets': effective_n,
            'energy': energy,
            'participation_ratio': participation_ratio,
            'max_amplitude': np.max(np.abs(psi_final)),
            'min_amplitude': np.min(np.abs(psi_final))
        }