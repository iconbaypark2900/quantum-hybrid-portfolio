"""
Financial graph construction module for QSW optimization.
Builds weighted graphs encoding correlations and return relationships.
"""
import numpy as np
import networkx as nx
from typing import Tuple, Dict, Optional
import warnings

from config.qsw_config import QSWConfig

class FinancialGraphBuilder:
    """
    Constructs financial graphs for quantum walk optimization.
    
    Key innovation: Adaptive graph density based on market regime.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize graph builder with configuration."""
        self.config = config or QSWConfig()
        
    def build_graph(self,
                   returns: np.ndarray,
                   covariance: np.ndarray,
                   market_regime: str = 'normal') -> Tuple[nx.Graph, Dict]:
        """
        Build weighted graph from financial data.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            market_regime: Current market regime
            
        Returns:
            Graph and metrics dictionary
        """
        n_assets = len(returns)
        
        # Calculate correlation from covariance
        std_dev = np.sqrt(np.diag(covariance))
        correlation = covariance / np.outer(std_dev, std_dev)
        
        # Get adaptive threshold
        threshold = self._get_adaptive_threshold(correlation, market_regime)
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes with attributes
        for i in range(n_assets):
            G.add_node(i, 
                      return_potential=returns[i],
                      risk=std_dev[i],
                      sharpe=returns[i] / std_dev[i] if std_dev[i] > 0 else 0)
        
        # Add weighted edges
        edge_count = 0
        total_weight = 0
        
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                if abs(correlation[i, j]) > threshold:
                    weight = self._calculate_edge_weight(
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
            metrics['clustering_coefficient'] = nx.average_clustering(G, weight='weight')
            
            # Check connectivity
            metrics['is_connected'] = nx.is_connected(G)
            metrics['n_components'] = nx.number_connected_components(G)
        else:
            warnings.warn("Graph has no edges. Consider lowering correlation threshold.")
            metrics['avg_degree'] = 0
            metrics['clustering_coefficient'] = 0
            metrics['is_connected'] = False
            metrics['n_components'] = n_assets
        
        return G, metrics
    
    def _get_adaptive_threshold(self, 
                               correlation: np.ndarray,
                               market_regime: str) -> float:
        """
        Calculate adaptive threshold based on market regime.
        
        Key insight: Different market conditions require different graph densities.
        """
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
    
    def _calculate_edge_weight(self,
                              correlation: float,
                              return_i: float,
                              return_j: float,
                              risk_i: float,
                              risk_j: float) -> float:
        """
        Calculate sophisticated edge weight.
        
        Combines multiple factors:
        - Correlation strength
        - Return similarity
        - Risk similarity
        - Diversification benefit
        """
        # Return similarity factor (assets with similar returns)
        return_diff = abs(return_i - return_j)
        max_return = max(abs(return_i), abs(return_j), 1e-6)
        return_similarity = np.exp(-return_diff / max_return)
        
        # Risk similarity factor
        risk_diff = abs(risk_i - risk_j)
        max_risk = max(risk_i, risk_j, 1e-6)
        risk_similarity = np.exp(-risk_diff / max_risk)
        
        # Diversification benefit (prefer low correlation)
        diversification_benefit = 1 - abs(correlation)
        
        # Combined weight with emphasis on correlation and diversification
        weight = (
            abs(correlation) * 0.4 +
            return_similarity * 0.2 +
            risk_similarity * 0.2 +
            diversification_benefit * 0.2
        )
        
        return weight