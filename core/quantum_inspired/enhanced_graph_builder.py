"""
Enhanced Financial graph construction module for QSW optimization.
This version includes improved edge weight calculations and additional features.
"""
import numpy as np
import networkx as nx
from typing import Tuple, Dict, Optional
import warnings
from sklearn.preprocessing import StandardScaler

from config.qsw_config import QSWConfig

class EnhancedFinancialGraphBuilder:
    """
    Enhanced financial graph construction with improved edge weight calculations.
    
    Key improvements:
    1. More sophisticated edge weight calculation
    2. Risk-return compatibility measures
    3. Sector-aware clustering
    4. Dynamic threshold adjustment
    """

    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize enhanced graph builder with configuration."""
        self.config = config or QSWConfig()

    def build_graph(self,
                   returns: np.ndarray,
                   covariance: np.ndarray,
                   market_regime: str = 'normal',
                   sectors: Optional[list] = None,
                   risk_factors: Optional[np.ndarray] = None) -> Tuple[nx.Graph, Dict]:
        """
        Build enhanced weighted graph from financial data.

        Args:
            returns: Expected returns
            covariance: Covariance matrix
            market_regime: Current market regime
            sectors: Sector classification for each asset (optional)
            risk_factors: Additional risk factors for each asset (optional)

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

        # Add nodes with enhanced attributes
        for i in range(n_assets):
            node_attrs = {
                'return_potential': returns[i],
                'risk': std_dev[i],
                'sharpe': returns[i] / std_dev[i] if std_dev[i] > 0 else 0,
                'volatility': std_dev[i]
            }
            
            # Add sector information if provided
            if sectors is not None and i < len(sectors):
                node_attrs['sector'] = sectors[i]
            
            # Add risk factors if provided
            if risk_factors is not None and i < len(risk_factors):
                node_attrs['risk_factors'] = risk_factors[i]
            
            G.add_node(i, **node_attrs)

        # Add weighted edges with enhanced calculations
        edge_count = 0
        total_weight = 0

        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                if abs(correlation[i, j]) > threshold:
                    # Use enhanced edge weight calculation
                    weight = self._calculate_enhanced_edge_weight(
                        correlation[i, j],
                        returns[i], returns[j],
                        std_dev[i], std_dev[j],
                        sectors[i] if sectors and i < len(sectors) else None,
                        sectors[j] if sectors and j < len(sectors) else None
                    )

                    if weight > self.config.min_edge_weight:
                        G.add_edge(i, j, 
                                 weight=weight, 
                                 correlation=correlation[i, j],
                                 abs_correlation=abs(correlation[i, j]),
                                 return_diff=abs(returns[i] - returns[j]),
                                 risk_diff=abs(std_dev[i] - std_dev[j]))

                        edge_count += 1
                        total_weight += weight

        # Calculate enhanced graph metrics
        metrics = {
            'n_nodes': n_assets,
            'n_edges': edge_count,
            'density': 2 * edge_count / (n_assets * (n_assets - 1)) if n_assets > 1 else 0,
            'threshold_used': threshold,
            'avg_weight': total_weight / edge_count if edge_count > 0 else 0,
            'regime': market_regime,
            'avg_correlation': np.mean(np.abs(correlation[np.triu_indices_from(correlation, k=1)])) if edge_count > 0 else 0
        }

        # Add graph theory metrics
        if G.number_of_edges() > 0:
            metrics['avg_degree'] = np.mean([d for n, d in G.degree()])
            metrics['clustering_coefficient'] = nx.average_clustering(G, weight='weight')
            metrics['assortativity'] = nx.degree_assortativity_coefficient(G, weight='weight')

            # Check connectivity
            metrics['is_connected'] = nx.is_connected(G)
            metrics['n_components'] = nx.number_connected_components(G)
            
            # Calculate centrality measures
            try:
                betweenness = nx.betweenness_centrality(G, weight='weight')
                metrics['avg_betweenness'] = np.mean(list(betweenness.values()))
                metrics['max_betweenness'] = max(betweenness.values())
            except:
                metrics['avg_betweenness'] = 0
                metrics['max_betweenness'] = 0
        else:
            warnings.warn("Graph has no edges. Consider lowering correlation threshold.")
            metrics.update({
                'avg_degree': 0,
                'clustering_coefficient': 0,
                'assortativity': 0,
                'is_connected': False,
                'n_components': n_assets,
                'avg_betweenness': 0,
                'max_betweenness': 0
            })

        return G, metrics

    def _get_adaptive_threshold(self,
                               correlation: np.ndarray,
                               market_regime: str) -> float:
        """
        Calculate adaptive threshold based on market regime and correlation distribution.
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
        mean_corr = np.mean(np.abs(correlation_values))

        # Adjust threshold based on correlation levels
        if mean_corr > 0.5:
            # High correlation environment - increase threshold
            threshold = base_threshold * 1.2
        elif mean_corr < 0.2:
            # Low correlation environment - decrease threshold
            threshold = base_threshold * 0.8
        else:
            threshold = base_threshold

        # Ensure threshold is within reasonable bounds
        threshold = np.clip(threshold, 0.05, 0.7)

        return threshold

    def _calculate_enhanced_edge_weight(self,
                                      correlation: float,
                                      return_i: float,
                                      return_j: float,
                                      risk_i: float,
                                      risk_j: float,
                                      sector_i: Optional[str] = None,
                                      sector_j: Optional[str] = None) -> float:
        """
        Enhanced edge weight calculation considering multiple factors:
        - Correlation strength and direction
        - Risk-return compatibility
        - Sector similarity
        - Diversification benefits
        """
        # Base correlation weight (higher correlation = stronger connection)
        base_weight = abs(correlation)
        
        # Sign-aware correlation (positive correlations may be treated differently than negative)
        signed_corr_weight = max(0, correlation)  # Only positive correlations contribute to similarity
        
        # Risk-return compatibility (assets with similar risk-return profiles may be grouped)
        # Calculate Sharpe ratio similarity
        sharpe_i = return_i / (risk_i + 1e-6)
        sharpe_j = return_j / (risk_j + 1e-6)
        sharpe_similarity = 1.0 - abs(sharpe_i - sharpe_j) / (abs(sharpe_i) + abs(sharpe_j) + 1e-6)
        
        # Return similarity (assets with similar returns may be grouped)
        return_similarity = 1.0 - abs(return_i - return_j) / (abs(return_i) + abs(return_j) + 1e-6)
        
        # Risk similarity (assets with similar risk may be grouped)
        risk_similarity = 1.0 - abs(risk_i - risk_j) / (risk_i + risk_j + 1e-6)
        
        # Sector similarity (same sector = higher similarity)
        sector_bonus = 0.1 if sector_i and sector_j and sector_i == sector_j else 0
        
        # Diversification factor (for diversification-focused approach)
        # This rewards low correlation for diversification purposes
        diversification_factor = 1.0 - abs(correlation)
        
        # Combine factors with appropriate weights
        # The weights can be tuned based on optimization objective
        weight = (
            0.4 * base_weight +           # 40% correlation strength
            0.15 * sharpe_similarity +    # 15% Sharpe similarity  
            0.15 * return_similarity +    # 15% return similarity
            0.15 * risk_similarity +      # 15% risk similarity
            0.1 * diversification_factor + # 10% diversification benefit
            sector_bonus                   # Sector bonus
        )
        
        return max(0, weight)

    def _calculate_diversification_weight(self,
                                        correlation: float,
                                        return_i: float,
                                        return_j: float,
                                        risk_i: float,
                                        risk_j: float) -> float:
        """
        Alternative weight calculation focused on diversification.
        Low correlation gets higher weight to encourage diversification.
        """
        # Invert correlation: low correlation = high weight
        diversification_weight = 1.0 - abs(correlation)

        # Scale by geometric mean of Sharpe ratios to reward diversification between good assets
        sharpe_i = return_i / (risk_i + 1e-6)
        sharpe_j = return_j / (risk_j + 1e-6)
        sharpe_product = np.sqrt(max(0, sharpe_i * sharpe_j))

        # Combine: reward diversification between good assets
        weight = diversification_weight * (1.0 + 0.5 * sharpe_product)

        return max(0, weight)

    def _calculate_mean_reversion_weight(self,
                                       correlation: float,
                                       return_i: float,
                                       return_j: float,
                                       risk_i: float,
                                       risk_j: float) -> float:
        """
        Weight calculation that considers mean reversion properties.
        Assets that are negatively correlated may provide mean reversion opportunities.
        """
        # Base weight on absolute correlation
        base_weight = abs(correlation)
        
        # If assets are negatively correlated, this could be good for mean reversion
        neg_corr_bonus = max(0, -correlation) * 0.5  # Bonus for negative correlation
        
        # Reward combinations with different risk levels for rebalancing opportunities
        risk_difference = abs(risk_i - risk_j) / (risk_i + risk_j + 1e-6)
        
        weight = base_weight + neg_corr_bonus + risk_difference * 0.1
        
        return max(0, weight)


class AdaptiveGraphBuilder:
    """
    Adaptive version that adjusts its behavior based on market conditions.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        self.config = config or QSWConfig()
        self.enhanced_builder = EnhancedFinancialGraphBuilder(config)
        
    def build_graph(self, 
                   returns: np.ndarray,
                   covariance: np.ndarray,
                   market_regime: str = 'normal',
                   sectors: Optional[list] = None,
                   objective: str = 'diversification') -> Tuple[nx.Graph, Dict]:
        """
        Build graph with adaptive strategy based on objective.
        
        Args:
            objective: 'diversification', 'momentum', 'mean_reversion', or 'balanced'
        """
        n_assets = len(returns)
        
        # Calculate correlation from covariance
        std_dev = np.sqrt(np.diag(covariance))
        correlation = covariance / np.outer(std_dev, std_dev)
        
        # Get adaptive threshold
        threshold = self.enhanced_builder._get_adaptive_threshold(correlation, market_regime)
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes with attributes
        for i in range(n_assets):
            G.add_node(i,
                      return_potential=returns[i],
                      risk=std_dev[i],
                      sharpe=returns[i] / std_dev[i] if std_dev[i] > 0 else 0)
        
        # Add weighted edges based on objective
        edge_count = 0
        total_weight = 0
        
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                if abs(correlation[i, j]) > threshold:
                    # Choose weight calculation based on objective
                    if objective == 'diversification':
                        weight = self.enhanced_builder._calculate_diversification_weight(
                            correlation[i, j], returns[i], returns[j], std_dev[i], std_dev[j])
                    elif objective == 'mean_reversion':
                        weight = self.enhanced_builder._calculate_mean_reversion_weight(
                            correlation[i, j], returns[i], returns[j], std_dev[i], std_dev[j])
                    else:  # balanced or momentum
                        weight = self.enhanced_builder._calculate_enhanced_edge_weight(
                            correlation[i, j], returns[i], returns[j], std_dev[i], std_dev[j])
                    
                    if weight > self.config.min_edge_weight:
                        G.add_edge(i, j, weight=weight, correlation=correlation[i, j])
                        edge_count += 1
                        total_weight += weight
        
        # Calculate metrics (reuse the same logic as EnhancedFinancialGraphBuilder)
        metrics = {
            'n_nodes': n_assets,
            'n_edges': edge_count,
            'density': 2 * edge_count / (n_assets * (n_assets - 1)) if n_assets > 1 else 0,
            'threshold_used': threshold,
            'avg_weight': total_weight / edge_count if edge_count > 0 else 0,
            'regime': market_regime,
            'objective': objective
        }
        
        if G.number_of_edges() > 0:
            metrics['avg_degree'] = np.mean([d for n, d in G.degree()])
            metrics['clustering_coefficient'] = nx.average_clustering(G, weight='weight')
            metrics['is_connected'] = nx.is_connected(G)
            metrics['n_components'] = nx.number_connected_components(G)
        else:
            metrics.update({
                'avg_degree': 0,
                'clustering_coefficient': 0,
                'is_connected': False,
                'n_components': n_assets
            })
        
        return G, metrics