"""
Performance optimization module for quantum-inspired portfolio optimization.
Contains optimized implementations of quantum algorithms and performance utilities.
"""
import numpy as np
import networkx as nx
from scipy.linalg import expm
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm as expm_sparse
from typing import Tuple, Dict, Optional
import time
from functools import wraps

from config.qsw_config import QSWConfig


def timing_decorator(func):
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper


class OptimizedQuantumEvolution:
    """
    Optimized quantum evolution engine with performance enhancements.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize optimized evolution engine."""
        self.config = config or QSWConfig()
        self._hamiltonian_cache = {}
        self._expm_cache = {}

    def evolve(self,
              graph: nx.Graph,
              omega: float,
              evolution_time: int,
              use_cache: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        Run optimized quantum-inspired evolution on graph.
        
        Optimizations:
        - Caching of Hamiltonian and evolution operators
        - Sparse matrix operations for large graphs
        - Numerical optimizations
        """
        n_nodes = graph.number_of_nodes()
        
        # Use cache if enabled and beneficial
        cache_key = None
        if use_cache and n_nodes < 100:  # Only cache for reasonably sized graphs
            cache_key = (id(graph), omega, evolution_time)
            if cache_key in self._expm_cache:
                U, H = self._expm_cache[cache_key]
            else:
                H = self._construct_hamiltonian_cached(graph, omega)
                U = self._compute_evolution_operator(H, evolution_time, n_nodes)
                self._expm_cache[cache_key] = (U, H)
        else:
            H = self._construct_hamiltonian_cached(graph, omega)
            U = self._compute_evolution_operator(H, evolution_time, n_nodes)

        # Initial state (equal superposition)
        psi_0 = np.ones(n_nodes, dtype=complex) / np.sqrt(n_nodes)

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
        
        # Add performance metrics
        metrics['nodes_processed'] = n_nodes
        metrics['used_cache'] = cache_key is not None and cache_key in self._expm_cache

        return weights, metrics

    def evolve_discrete_time(self, graph: nx.Graph, omega: float,
                             evolution_time: int, n_steps: int = 10) -> Tuple[np.ndarray, Dict]:
        """Discrete-time quantum walk evolution. Delegates to evolve() for compatibility."""
        weights, metrics = self.evolve(graph, omega, evolution_time)
        metrics['evolution_type'] = 'discrete'
        metrics['n_steps'] = n_steps
        return weights, metrics

    def evolve_with_decoherence(self, graph: nx.Graph, omega: float,
                                evolution_time: int, decoherence_rate: float = 0.05) -> Tuple[np.ndarray, Dict]:
        """Decoherent quantum walk evolution. Delegates to evolve() for compatibility."""
        weights, metrics = self.evolve(graph, omega, evolution_time)
        metrics['evolution_type'] = 'decoherent'
        metrics['decoherence_rate'] = decoherence_rate
        return weights, metrics

    def _construct_hamiltonian_cached(self, graph: nx.Graph, omega: float) -> np.ndarray:
        """Construct Hamiltonian with caching."""
        n = graph.number_of_nodes()
        cache_key = (id(graph), omega)
        
        if cache_key in self._hamiltonian_cache:
            return self._hamiltonian_cache[cache_key]
        
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
        
        # Cache the result
        self._hamiltonian_cache[cache_key] = H
        return H

    def _compute_evolution_operator(self, H: np.ndarray, evolution_time: int, n_nodes: int):
        """Compute evolution operator with optimized method selection."""
        if n_nodes > 100:
            # Use sparse matrix for large graphs
            H_sparse = csr_matrix(H)
            U = expm_sparse(-1j * H_sparse * evolution_time).toarray()
        else:
            # Use dense matrix for small graphs (often faster due to overhead)
            U = expm(-1j * H * evolution_time)
        return U

    def _calculate_evolution_metrics(self,
                                    psi_0: np.ndarray,
                                    psi_final: np.ndarray,
                                    H: np.ndarray,
                                    U: np.ndarray,
                                    weights: np.ndarray) -> Dict:
        """Calculate metrics about the evolution process with optimizations."""
        n = len(weights)

        # State overlap (how much did state change)
        overlap = np.abs(np.dot(np.conj(psi_0), psi_final)) ** 2

        # Entropy of final distribution (diversification measure)
        # Use optimized calculation
        weights_nonzero = weights[weights > 1e-10]
        if len(weights_nonzero) > 0:
            entropy = -np.sum(weights_nonzero * np.log(weights_nonzero))
        else:
            entropy = 0.0

        # Effective number of assets (from entropy)
        effective_n = np.exp(entropy) if entropy > 0 else 0

        # Energy expectation value
        energy = np.real(np.dot(np.conj(psi_final), H @ psi_final))

        # Participation ratio (another diversification measure)
        participation_ratio = 1 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0

        return {
            'state_overlap': overlap,
            'entropy': entropy,
            'effective_n_assets': effective_n,
            'energy': energy,
            'participation_ratio': participation_ratio,
            'max_amplitude': np.max(np.abs(psi_final)),
            'min_amplitude': np.min(np.abs(psi_final)),
            'concentration': 1 - np.sum(weights ** 2),  # 1 - HHI
            'hhi': np.sum(weights ** 2)
        }

    def clear_cache(self):
        """Clear internal caches."""
        self._hamiltonian_cache.clear()
        self._expm_cache.clear()


class OptimizedGraphBuilder:
    """
    Optimized graph construction with performance enhancements.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize optimized graph builder."""
        self.config = config or QSWConfig()

    def build_graph(self,
                   returns: np.ndarray,
                   covariance: np.ndarray,
                   market_regime: str = 'normal') -> Tuple[nx.Graph, Dict]:
        """
        Build weighted graph from financial data with optimizations.
        """
        n_assets = len(returns)

        # Calculate correlation from covariance using vectorized operations
        std_dev = np.sqrt(np.diag(covariance))
        correlation = covariance / np.outer(std_dev, std_dev)

        # Get adaptive threshold
        threshold = self._get_adaptive_threshold(correlation, market_regime)

        # Create graph using vectorized operations where possible
        G = nx.Graph()

        # Add all nodes first (required so graph has n_assets nodes for weight alignment)
        node_attrs = {}
        for i in range(n_assets):
            G.add_node(i)
            node_attrs[i] = {
                'return_potential': returns[i],
                'risk': std_dev[i],
                'sharpe': returns[i] / std_dev[i] if std_dev[i] > 0 else 0
            }
        nx.set_node_attributes(G, node_attrs)

        # Vectorized edge creation with filtering
        edge_count = 0
        total_weight = 0
        
        # Use upper triangle to avoid duplicate edges
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                if abs(correlation[i, j]) > threshold:
                    weight = self._calculate_edge_weight_simple(
                        correlation[i, j],
                        returns[i], returns[j],
                        std_dev[i], std_dev[j]
                    )

                    if weight > self.config.min_edge_weight:
                        G.add_edge(i, j, weight=weight, correlation=correlation[i, j])
                        edge_count += 1
                        total_weight += weight

        # Calculate graph metrics
        metrics = {
            'n_nodes': n_assets,
            'n_edges': edge_count,
            'density': 2 * edge_count / (n_assets * (n_assets - 1)) if n_assets > 1 else 0,
            'threshold_used': threshold,
            'avg_weight': total_weight / edge_count if edge_count > 0 else 0,
            'regime': market_regime
        }

        # Add graph theory metrics
        if G.number_of_edges() > 0:
            metrics['avg_degree'] = np.mean([d for n, d in G.degree()])
            metrics['clustering_coefficient'] = nx.algorithms.cluster.average_clustering(G, weight='weight')

            # Check connectivity
            metrics['is_connected'] = nx.is_connected(G)
            metrics['n_components'] = nx.number_connected_components(G)
        else:
            metrics['avg_degree'] = 0
            metrics['clustering_coefficient'] = 0
            metrics['is_connected'] = False
            metrics['n_components'] = n_assets

        return G, metrics

    def _get_adaptive_threshold(self,
                               correlation: np.ndarray,
                               market_regime: str) -> float:
        """Calculate adaptive threshold with optimizations."""
        if not self.config.adaptive_threshold:
            return self.config.correlation_threshold

        # Use regime-specific thresholds
        base_threshold = self.config.regime_thresholds.get(
            market_regime,
            self.config.correlation_threshold
        )

        # Further adapt based on correlation distribution
        correlation_values = correlation[np.triu_indices_from(correlation, k=1)]
        median_corr = np.median(np.abs(correlation_values))

        # Adjust threshold based on median correlation
        if median_corr > 0.5:
            # High correlation environment - increase threshold
            threshold = base_threshold * 1.2
        elif median_corr < 0.2:
            # Low correlation environment - decrease threshold
            threshold = base_threshold * 0.8
        else:
            threshold = base_threshold

        return np.clip(threshold, 0.1, 0.6)

    def _calculate_edge_weight_simple(self,
                                      correlation: float,
                                      return_i: float,
                                      return_j: float,
                                      risk_i: float,
                                      risk_j: float) -> float:
        """Optimized edge weight calculation."""
        # Primary weight: correlation strength
        weight = abs(correlation)

        # Optional: Small boost for similar risk/return profiles
        # This helps cluster assets by characteristics
        return_similarity = 1.0 - abs(return_i - return_j) / (abs(return_i) + abs(return_j) + 1e-6)
        risk_similarity = 1.0 - abs(risk_i - risk_j) / (risk_i + risk_j + 1e-6)

        # Combine: 80% correlation, 20% similarity
        weight = 0.8 * abs(correlation) + 0.1 * return_similarity + 0.1 * risk_similarity

        return weight


class PerformanceProfiler:
    """
    Utility class for profiling performance of quantum algorithms.
    """
    
    def __init__(self):
        self.profiles = {}
    
    @timing_decorator
    def profile_evolution(self, evolution_engine, graph, omega, evolution_time):
        """Profile the evolution process."""
        return evolution_engine.evolve(graph, omega, evolution_time)
    
    @timing_decorator
    def profile_graph_building(self, graph_builder, returns, covariance, regime):
        """Profile the graph building process."""
        return graph_builder.build_graph(returns, covariance, regime)
    
    def run_performance_comparison(self, n_assets_list=[10, 20, 50, 100]):
        """Run performance comparison across different portfolio sizes."""
        import networkx as nx
        
        results = {}
        
        for n_assets in n_assets_list:
            print(f"\nTesting with {n_assets} assets...")
            
            # Generate test data
            returns = np.random.randn(n_assets) * 0.1 + 0.05
            A = np.random.randn(n_assets, n_assets)
            covariance = np.dot(A.T, A) / n_assets
            
            # Create graph
            graph_builder = OptimizedGraphBuilder()
            graph, _ = graph_builder.build_graph(returns, covariance)
            
            # Profile evolution
            evolution_engine = OptimizedQuantumEvolution()
            start_time = time.time()
            weights, metrics = evolution_engine.evolve(graph, 0.3, 10)
            evolution_time = time.time() - start_time
            
            results[n_assets] = {
                'evolution_time': evolution_time,
                'nodes_processed': metrics.get('nodes_processed', n_assets),
                'used_cache': metrics.get('used_cache', False)
            }
            
            print(f"  Evolution time: {evolution_time:.4f}s")
            print(f"  Nodes processed: {metrics.get('nodes_processed', n_assets)}")
            print(f"  Used cache: {metrics.get('used_cache', False)}")
        
        return results


def optimize_portfolio_computations(returns: np.ndarray, 
                                  covariance: np.ndarray) -> Dict:
    """
    Optimized portfolio metric computations.
    """
    # Vectorized computation of portfolio metrics
    n = len(returns)
    
    # Precompute commonly used values
    sqrt_cov_diag = np.sqrt(np.diag(covariance))
    
    def compute_metrics_vectorized(weights):
        """Vectorized computation of portfolio metrics."""
        # Expected return
        portfolio_return = np.dot(weights, returns)
        
        # Portfolio variance using quadratic form
        portfolio_variance = np.dot(weights, np.dot(covariance, weights))
        portfolio_volatility = np.sqrt(np.maximum(portfolio_variance, 1e-12))  # Prevent sqrt of negative
        
        # Sharpe ratio (avoid division by zero)
        sharpe_ratio = np.where(
            portfolio_volatility > 1e-12,
            portfolio_return / portfolio_volatility,
            0.0
        )
        
        # Diversification metrics
        n_assets_eff = 1 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0
        herfindahl_index = np.sum(weights ** 2)
        
        return {
            'expected_return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'n_assets_effective': n_assets_eff,
            'herfindahl_index': herfindahl_index
        }
    
    return compute_metrics_vectorized


if __name__ == "__main__":
    # Example usage and performance testing
    profiler = PerformanceProfiler()
    
    print("Running performance comparison...")
    results = profiler.run_performance_comparison(n_assets_list=[10, 20, 50])
    
    print("\nPerformance Summary:")
    for n_assets, metrics in results.items():
        print(f"{n_assets:3d} assets: {metrics['evolution_time']:6.4f}s")