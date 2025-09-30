"""
Configuration for Quantum Stochastic Walk optimizer.
Based on optimal parameters from Chang et al. (2025).
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
    evolution_time: int = 100
    
    # Graph construction parameters
    correlation_threshold: float = 0.3
    adaptive_threshold: bool = True
    min_edge_weight: float = 0.01
    
    # Stability enhancement parameters
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

# Default configuration instance
DEFAULT_CONFIG = QSWConfig()