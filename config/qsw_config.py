"""
Configuration for Quantum Stochastic Walk optimizer - FIXED VERSION
Key fix: Reduced evolution_time from 100 to 10 to prevent over-smoothing
"""
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import yaml

@dataclass
class QSWConfig:
    """Configuration parameters for Quantum Stochastic Walk."""
    
    # Core QSW parameters (optimal from Chang et al.)
    omega_range: Tuple[float, float] = (0.2, 0.4)
    default_omega: float = 0.3
    
    # FIX: Reduced evolution_time from 100 to 10
    # REASON: evolution_time=100 causes over-smoothing where all portfolios
    # converge to similar weights (high overlap ~0.87). Lower time allows
    # more differentiation while still being stable.
    evolution_time: int = 10
    
    # Graph construction parameters
    correlation_threshold: float = 0.3
    adaptive_threshold: bool = True
    min_edge_weight: float = 0.01
    
    # Stability enhancement parameters
    # Note: Consider relaxing max_turnover if getting zero turnover
    max_turnover: float = 0.2  # 20% maximum turnover
    stability_blend_factor: float = 0.7  # 70% new, 30% old
    
    # Portfolio constraints
    min_weight: float = 0.001  # 0.1% minimum position
    max_weight: float = 0.10   # 10% maximum position
    min_assets: int = 10       # Minimum number of assets
    max_assets: int = 100      # Maximum number of assets
    
    # Market regime parameters
    regime_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        """Set default regime thresholds if not provided."""
        if self.regime_thresholds is None:
            self.regime_thresholds = {
                'bull': 0.4,      # Sparser graph
                'bear': 0.25,     # Denser graph
                'volatile': 0.2,  # Most connections
                'normal': 0.3     # Standard threshold
            }
    
    @classmethod
    def from_yaml(cls, filepath: str):
        """Load configuration from YAML file."""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
    
    def get_omega_for_regime(self, regime: str) -> float:
        """Get optimal omega parameter for market regime."""
        omega_adjustments = {
            'bull': 0.35,     # Higher momentum
            'bear': 0.25,     # Lower momentum
            'volatile': 0.30, # Balanced
            'normal': 0.30    # Default
        }
        return omega_adjustments.get(regime, self.default_omega)
    
    @classmethod
    def create_aggressive_config(cls):
        """
        Create configuration for more aggressive optimization.
        - Lower evolution time for more differentiation
        - Higher turnover tolerance
        """
        return cls(
            evolution_time=5,
            max_turnover=0.3,
            stability_blend_factor=0.8
        )
    
    @classmethod
    def create_conservative_config(cls):
        """
        Create configuration for more conservative optimization.
        - Higher evolution time for more smoothing
        - Lower turnover tolerance
        """
        return cls(
            evolution_time=20,
            max_turnover=0.10,
            stability_blend_factor=0.6
        )

# Default configuration instance
DEFAULT_CONFIG = QSWConfig()

# Notes on evolution_time tuning:
# - evolution_time in [1-5]: Very responsive, high differentiation, may be unstable
# - evolution_time in [5-15]: Good balance (RECOMMENDED RANGE after fix)
# - evolution_time in [15-50]: Stable but less differentiation
# - evolution_time > 50: Over-smoothed, approaches equal weights
#
# The original value of 100 was too high and caused portfolios to converge
# to nearly identical weights regardless of input data.