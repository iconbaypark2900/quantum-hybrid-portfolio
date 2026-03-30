"""
Enhanced stability enhancement module for improved turnover reduction.
This version includes more sophisticated stabilization techniques.
"""
import numpy as np
from typing import Optional, Tuple
from config.qsw_config import QSWConfig
import warnings

class EnhancedStabilityEnhancer:
    """
    Enhanced stability enhancement with multiple techniques for turnover reduction.
    
    Key improvements:
    1. Multi-factor blending (momentum, mean-reversion, trend-following)
    2. Dynamic threshold adjustment
    3. Risk-aware stabilization
    4. Regime-adaptive blending
    """

    def __init__(self, config: Optional[QSWConfig] = None):
        """Initialize enhanced stability enhancer."""
        self.config = config or QSWConfig()
        self.turnover_history = []
        self.performance_history = []
        self.market_regime_history = []

    def stabilize(self,
                 new_weights: np.ndarray,
                 old_weights: np.ndarray,
                 market_regime: str = 'normal',
                 risk_adjustment: Optional[np.ndarray] = None,
                 momentum_factor: Optional[np.ndarray] = None,
                 market_volatility: Optional[float] = None) -> np.ndarray:
        """
        Apply enhanced stability enhancement to reduce turnover.

        Args:
            new_weights: Newly optimized weights
            old_weights: Previous period weights
            market_regime: Current market regime
            risk_adjustment: Risk adjustment factors for each asset
            momentum_factor: Momentum factors for each asset
            market_volatility: Current market volatility (optional)

        Returns:
            Stabilized weights with reduced turnover
        """
        # Validate inputs
        if len(new_weights) != len(old_weights):
            raise ValueError("New and old weights must have the same length")
        
        # Calculate proposed turnover
        proposed_turnover = self._calculate_turnover(new_weights, old_weights)

        # Determine adaptive blending based on multiple factors
        blend_factor = self._calculate_enhanced_blend_factor(
            proposed_turnover,
            market_regime,
            market_volatility,
            risk_adjustment
        )

        # Apply multi-factor stabilization
        stabilized_weights = self._apply_multi_factor_stabilization(
            new_weights,
            old_weights,
            blend_factor,
            risk_adjustment,
            momentum_factor,
            market_regime
        )

        # Apply post-processing to ensure constraints
        final_weights = self._apply_post_processing(
            stabilized_weights,
            old_weights,
            market_regime
        )

        # Track turnover and performance
        actual_turnover = self._calculate_turnover(final_weights, old_weights)
        self.turnover_history.append({
            'proposed': proposed_turnover,
            'actual': actual_turnover,
            'reduction': 1 - actual_turnover / proposed_turnover if proposed_turnover > 0 else 0,
            'blend_factor': blend_factor,
            'regime': market_regime
        })

        return final_weights

    def _calculate_enhanced_blend_factor(self,
                                       proposed_turnover: float,
                                       market_regime: str,
                                       market_volatility: Optional[float] = None,
                                       risk_adjustment: Optional[np.ndarray] = None) -> float:
        """
        Calculate adaptive blending factor based on multiple factors.
        
        Higher volatility → more stability (lower blend factor)
        Higher turnover → more stability needed
        Different regimes → different optimal blend factors
        """
        # Base blend factor based on regime
        regime_factors = {
            'bull': 0.75,      # More aggressive in bull markets
            'bear': 0.65,      # More conservative in bear markets  
            'volatile': 0.55,  # Very conservative in volatile markets
            'normal': 0.70     # Balanced in normal markets
        }
        base_factor = regime_factors.get(market_regime, self.config.stability_blend_factor)

        # Adjust for excessive turnover
        if proposed_turnover > self.config.max_turnover:
            turnover_ratio = self.config.max_turnover / proposed_turnover
            turnover_adjustment = np.clip(turnover_ratio, 0.3, 1.0)
        else:
            turnover_adjustment = 1.0

        # Adjust for market volatility if provided
        if market_volatility is not None:
            # Higher volatility → be more conservative
            volatility_adjustment = np.exp(-market_volatility * 5)
            volatility_adjustment = np.clip(volatility_adjustment, 0.4, 1.0)
        else:
            volatility_adjustment = 1.0

        # Adjust for risk if provided
        if risk_adjustment is not None:
            # Average risk across portfolio
            avg_risk = np.mean(risk_adjustment)
            # Higher risk → more conservative
            risk_adjustment_factor = np.exp(-avg_risk * 2)
            risk_adjustment_factor = np.clip(risk_adjustment_factor, 0.5, 1.0)
        else:
            risk_adjustment_factor = 1.0

        # Final blend factor
        blend_factor = (base_factor * 
                       turnover_adjustment * 
                       volatility_adjustment * 
                       risk_adjustment_factor)

        return np.clip(blend_factor, 0.2, 0.9)

    def _apply_multi_factor_stabilization(self,
                                         new_weights: np.ndarray,
                                         old_weights: np.ndarray,
                                         blend_factor: float,
                                         risk_adjustment: Optional[np.ndarray] = None,
                                         momentum_factor: Optional[np.ndarray] = None,
                                         market_regime: str = 'normal') -> np.ndarray:
        """
        Apply stabilization using multiple factors.
        """
        n_assets = len(new_weights)

        # Base blending
        blended_weights = blend_factor * new_weights + (1 - blend_factor) * old_weights

        # Apply risk adjustment if provided
        if risk_adjustment is not None:
            # Adjust weights based on risk profile
            risk_normalized = risk_adjustment / np.mean(risk_adjustment) if np.mean(risk_adjustment) > 0 else np.ones(n_assets)
            # Reduce weights of high-risk assets slightly
            risk_adjusted_weights = blended_weights * (1.0 - 0.1 * (risk_normalized - 1.0))
            risk_adjusted_weights = np.maximum(risk_adjusted_weights, 0)  # Ensure non-negative
        else:
            risk_adjusted_weights = blended_weights

        # Apply momentum adjustment if provided
        if momentum_factor is not None:
            # Adjust based on momentum (positive momentum gets slight boost)
            momentum_normalized = momentum_factor / np.mean(np.abs(momentum_factor)) if np.mean(np.abs(momentum_factor)) > 0 else np.zeros(n_assets)
            # Apply momentum adjustment (more aggressive in bull markets)
            momentum_boost = 0.05 if market_regime == 'bull' else 0.02
            momentum_weights = risk_adjusted_weights * (1.0 + momentum_boost * momentum_normalized)
            momentum_weights = np.maximum(momentum_weights, 0)  # Ensure non-negative
        else:
            momentum_weights = risk_adjusted_weights

        # Renormalize
        final_weights = momentum_weights / np.sum(momentum_weights)

        return final_weights

    def _apply_post_processing(self,
                             weights: np.ndarray,
                             old_weights: np.ndarray,
                             market_regime: str = 'normal') -> np.ndarray:
        """
        Apply post-processing to ensure constraints and stability.
        """
        # Ensure weights are non-negative
        weights = np.maximum(weights, 0)

        # Apply minimum weight constraint
        min_weight_mask = weights < self.config.min_weight
        if np.any(min_weight_mask):
            # Move small weights to zero and redistribute
            redistributed_amount = np.sum(weights[min_weight_mask])
            weights[min_weight_mask] = 0
            remaining_assets = weights > 0
            if np.sum(remaining_assets) > 0:
                weights[remaining_assets] += redistributed_amount / np.sum(remaining_assets)

        # Apply maximum weight constraint
        excess_mask = weights > self.config.max_weight
        if np.any(excess_mask):
            # Clip to maximum and redistribute excess
            excess_total = np.sum(weights[excess_mask] - self.config.max_weight)
            weights[excess_mask] = self.config.max_weight
            remaining_assets = weights < self.config.max_weight
            if np.sum(remaining_assets) > 0:
                weights[remaining_assets] += excess_total * (weights[remaining_assets] / np.sum(weights[remaining_assets]))

        # Final renormalization
        weights = weights / np.sum(weights)

        # Additional stability check: if the change is very small, preserve more of old weights
        total_change = np.sum(np.abs(weights - old_weights))
        if total_change < 0.01:  # Less than 1% total change
            # This is already a very stable solution, return as is
            pass
        elif total_change > 0.3:  # More than 30% total change
            # Too much change, apply additional smoothing
            weights = 0.8 * weights + 0.2 * old_weights
            weights = weights / np.sum(weights)

        return weights

    def _calculate_turnover(self,
                          new_weights: np.ndarray,
                          old_weights: np.ndarray) -> float:
        """Calculate portfolio turnover."""
        return np.sum(np.abs(new_weights - old_weights)) / 2

    def get_turnover_statistics(self) -> dict:
        """Get comprehensive turnover reduction statistics."""
        if not self.turnover_history:
            return {}

        turnovers = [h['actual'] for h in self.turnover_history]
        reductions = [h['reduction'] for h in self.turnover_history]
        blend_factors = [h['blend_factor'] for h in self.turnover_history]

        # Calculate statistics by regime if available
        regime_stats = {}
        if self.turnover_history and 'regime' in self.turnover_history[0]:
            regimes = set(h['regime'] for h in self.turnover_history)
            for regime in regimes:
                regime_data = [h for h in self.turnover_history if h['regime'] == regime]
                if regime_data:
                    regime_turnovers = [h['actual'] for h in regime_data]
                    regime_reductions = [h['reduction'] for h in regime_data]
                    regime_stats[regime] = {
                        'avg_turnover': np.mean(regime_turnovers),
                        'avg_reduction': np.mean(regime_reductions),
                        'count': len(regime_data)
                    }

        return {
            'avg_turnover': np.mean(turnovers),
            'median_turnover': np.median(turnovers),
            'max_turnover': np.max(turnovers),
            'min_turnover': np.min(turnovers),
            'avg_reduction': np.mean(reductions),
            'median_reduction': np.median(reductions),
            'max_reduction': np.max(reductions),
            'min_reduction': np.min(reductions),
            'avg_blend_factor': np.mean(blend_factors),
            'total_iterations': len(self.turnover_history),
            'regime_statistics': regime_stats,
            'turnover_std': np.std(turnovers),
            'reduction_std': np.std(reductions)
        }

    def get_performance_impact(self) -> dict:
        """
        Calculate the performance impact of stabilization.
        This would typically require backtesting data to be meaningful.
        """
        if not self.performance_history:
            return {}

        # Placeholder for performance impact analysis
        # In a real implementation, this would compare performance metrics
        # with and without stabilization
        return {
            'performance_impact_calculated': False,
            'requires_backtesting': True
        }

    def adaptive_learning_update(self, performance_feedback: Optional[dict] = None):
        """
        Update internal parameters based on performance feedback.
        This enables the system to learn and adapt over time.
        """
        if not self.turnover_history:
            return

        # Calculate recent trends
        recent_history = self.turnover_history[-10:] if len(self.turnover_history) >= 10 else self.turnover_history
        avg_recent_reduction = np.mean([h['reduction'] for h in recent_history])

        # Adjust parameters based on effectiveness
        if avg_recent_reduction < 0.1:  # Reduction is too low
            # Increase stability (reduce blend factor)
            self.config.stability_blend_factor = max(0.5, self.config.stability_blend_factor * 0.95)
        elif avg_recent_reduction > 0.8:  # Reduction is very high
            # Can afford to be more aggressive (increase blend factor)
            self.config.stability_blend_factor = min(0.9, self.config.stability_blend_factor * 1.02)

        # Update max_turnover based on market conditions if needed
        if len(self.turnover_history) >= 20:
            historical_avg = np.mean([h['actual'] for h in self.turnover_history[-20:]])
            # Adjust max_turnover to be slightly above historical average
            self.config.max_turnover = min(0.3, max(0.1, historical_avg * 1.2))


class RegimeAwareStabilityEnhancer(EnhancedStabilityEnhancer):
    """
    Regime-aware version that adapts its behavior based on market conditions.
    """
    
    def __init__(self, config: Optional[QSWConfig] = None):
        super().__init__(config)
        self.regime_parameters = {
            'bull': {
                'stability_blend_factor': 0.75,
                'max_turnover': 0.25,
                'momentum_sensitivity': 0.1
            },
            'bear': {
                'stability_blend_factor': 0.60,
                'max_turnover': 0.15,
                'momentum_sensitivity': 0.05
            },
            'volatile': {
                'stability_blend_factor': 0.50,
                'max_turnover': 0.10,
                'momentum_sensitivity': 0.02
            },
            'normal': {
                'stability_blend_factor': 0.70,
                'max_turnover': 0.20,
                'momentum_sensitivity': 0.07
            }
        }

    def stabilize(self,
                 new_weights: np.ndarray,
                 old_weights: np.ndarray,
                 market_regime: str = 'normal',
                 risk_adjustment: Optional[np.ndarray] = None,
                 momentum_factor: Optional[np.ndarray] = None,
                 market_volatility: Optional[float] = None) -> np.ndarray:
        """
        Apply regime-aware stabilization.
        """
        # Temporarily update config based on regime
        original_blend_factor = self.config.stability_blend_factor
        original_max_turnover = self.config.max_turnover
        
        regime_params = self.regime_parameters.get(market_regime, self.regime_parameters['normal'])
        self.config.stability_blend_factor = regime_params['stability_blend_factor']
        self.config.max_turnover = regime_params['max_turnover']
        
        # Apply stabilization
        result = super().stabilize(
            new_weights, old_weights, market_regime, 
            risk_adjustment, momentum_factor, market_volatility
        )
        
        # Restore original config
        self.config.stability_blend_factor = original_blend_factor
        self.config.max_turnover = original_max_turnover
        
        return result