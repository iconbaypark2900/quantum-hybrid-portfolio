"""
Portfolio optimization methods (re-exported from submodules).

Provides core.optimizers.* import path for use by unified portfolio service.
Imports from submodules to avoid name shadowing when submodules are loaded.
"""

from core.optimizers.equal_weight import equal_weight
from core.optimizers.markowitz import markowitz_max_sharpe, min_variance, target_return_frontier
from core.optimizers.hrp import hrp_weights
from core.optimizers.qubo_sa import qubo_sa_weights
from core.optimizers.vqe import vqe_weights
from core.optimizers.hybrid_pipeline import HybridPipelineInfo, hybrid_pipeline_weights

__all__ = [
    "equal_weight",
    "markowitz_max_sharpe",
    "min_variance",
    "target_return_frontier",
    "hrp_weights",
    "qubo_sa_weights",
    "vqe_weights",
    "hybrid_pipeline_weights",
    "HybridPipelineInfo",
]
