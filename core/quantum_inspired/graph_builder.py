"""
Financial graph construction module for QSW optimization - FIXED VERSION
Key fix: Simplified edge weight calculation that doesn't contradict itself
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
                    # FIX: Simplified edge weight calculation
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
    
    def _calculate_edge_weight_simple(self,
                                      correlation: float,
                                      return_i: float,
                                      return_j: float,
                                      risk_i: float,
                                      risk_j: float) -> float:
        """
        FIX: Simplified edge weight calculation.
        
        OLD PROBLEM: Used both correlation AND (1-correlation), canceling signal
        NEW APPROACH: Just use absolute correlation strength
        
        This gives the graph clear, interpretable structure:
        - High correlation = strong edge = assets move together
        - Low correlation = weak/no edge = assets independent
        """
        # Primary weight: correlation strength
        # Strong correlations (positive or negative) create strong edges
        weight = abs(correlation)
        
        # Optional: Small boost for similar risk/return profiles
        # This helps cluster assets by characteristics
        return_similarity = 1.0 - abs(return_i - return_j) / (abs(return_i) + abs(return_j) + 1e-6)
        risk_similarity = 1.0 - abs(risk_i - risk_j) / (risk_i + risk_j + 1e-6)
        
        # Combine: 80% correlation, 20% similarity
        weight = 0.8 * abs(correlation) + 0.1 * return_similarity + 0.1 * risk_similarity
        
        return weight
    
    def _calculate_edge_weight_diversification_focused(self,
                                                       correlation: float,
                                                       return_i: float,
                                                       return_j: float,
                                                       risk_i: float,
                                                       risk_j: float) -> float:
        """
        Alternative: Diversification-focused weighting.
        
        Use this if you want quantum walk to prefer uncorrelated assets.
        Inverts correlation so low correlation = strong edge.
        """
        # Invert correlation: low correlation = high weight
        diversification_weight = 1.0 - abs(correlation)
        
        # Scale by geometric mean of Sharpe ratios
        sharpe_i = return_i / (risk_i + 1e-6)
        sharpe_j = return_j / (risk_j + 1e-6)
        sharpe_product = np.sqrt(max(0, sharpe_i * sharpe_j))
        
        # Combine: reward diversification between good assets
        weight = diversification_weight * (1.0 + 0.5 * sharpe_product)
        
        return max(0, weight)