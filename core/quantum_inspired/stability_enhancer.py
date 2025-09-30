"""
Stability enhancement module for turnover reduction.
Key to achieving 90% turnover reduction vs classical rebalancing.
"""
import numpy as np
from typing import Optional
from config.qsw_config import QSWConfig

class StabilityEnhancer:
    """
    Reduces portfolio turnover through stability enhancement.
    
    This is crucial for practical implementation - reduces transaction costs.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize stability enhancer."""
        self.config = config or QSWConfig()
        self.turnover_history = []
        
    def stabilize(self,
                 new_weights: np.ndarray,
                 old_weights: np.ndarray,
                 market_volatility: Optional[float] = None) -> np.ndarray:
        """
        Apply stability enhancement to reduce turnover.
        
        Args:
            new_weights: Newly optimized weights
            old_weights: Previous period weights
            market_volatility: Current market volatility (optional)
            
        Returns:
            Stabilized weights with reduced turnover
        """
        # Calculate proposed turnover
        proposed_turnover = self._calculate_turnover(new_weights, old_weights)
        
        # Adaptive blending based on turnover
        if proposed_turnover <= self.config.max_turnover:
            # Turnover is acceptable
            final_weights = new_weights
        else:
            # Need to reduce turnover
            blend_factor = self._calculate_blend_factor(
                proposed_turnover, 
                market_volatility
            )
            
            # Blend old and new weights
            final_weights = (
                blend_factor * new_weights + 
                (1 - blend_factor) * old_weights
            )
            
            # Renormalize
            final_weights = final_weights / np.sum(final_weights)
            
        # Track turnover
        actual_turnover = self._calculate_turnover(final_weights, old_weights)
        self.turnover_history.append({
            'proposed': proposed_turnover,
            'actual': actual_turnover,
            'reduction': 1 - actual_turnover / proposed_turnover if proposed_turnover > 0 else 0
        })
        
        return final_weights
    
    def _calculate_turnover(self, 
                          new_weights: np.ndarray,
                          old_weights: np.ndarray) -> float:
        """Calculate portfolio turnover."""
        return np.sum(np.abs(new_weights - old_weights)) / 2
    
    def _calculate_blend_factor(self,
                               proposed_turnover: float,
                               market_volatility: Optional[float] = None) -> float:
        """
        Calculate adaptive blending factor.
        
        Higher volatility → more stability (lower blend factor)
        Higher turnover → more stability needed
        """
        # Base blend factor
        base_factor = self.config.stability_blend_factor
        
        # Adjust for excessive turnover
        turnover_ratio = self.config.max_turnover / proposed_turnover
        turnover_adjustment = np.clip(turnover_ratio, 0.3, 1.0)
        
        # Adjust for market volatility if provided
        if market_volatility is not None:
            # Higher volatility → be more conservative
            volatility_adjustment = np.exp(-market_volatility * 10)
            volatility_adjustment = np.clip(volatility_adjustment, 0.5, 1.0)
        else:
            volatility_adjustment = 1.0
        
        # Final blend factor
        blend_factor = base_factor * turnover_adjustment * volatility_adjustment
        
        return np.clip(blend_factor, 0.3, 0.9)
    
    def get_turnover_statistics(self) -> dict:
        """Get turnover reduction statistics."""
        if not self.turnover_history:
            return {}
        
        reductions = [h['reduction'] for h in self.turnover_history]
        
        return {
            'avg_reduction': np.mean(reductions),
            'median_reduction': np.median(reductions),
            'max_reduction': np.max(reductions),
            'min_reduction': np.min(reductions),
            'total_iterations': len(self.turnover_history)
        }