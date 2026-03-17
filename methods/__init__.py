"""
Portfolio optimization methods extracted from research notebooks.

Methods:
- equal_weight       : 1/N baseline
- markowitz          : Max-Sharpe via SLSQP (Markowitz 1952)
- hrp                : Hierarchical Risk Parity (López de Prado 2016)
- qubo_sa            : QUBO + Simulated Annealing (Orús et al. 2019)
- vqe                : VQE PauliTwoDesign (Scientific Reports 2023)
- hybrid_pipeline    : 3-Stage Hybrid (Buonaiuto/Springer 2025, Herman/arXiv 2025)
"""

from .equal_weight import equal_weight
from .markowitz import markowitz_max_sharpe, min_variance, target_return_frontier
from .hrp import hrp_weights
from .qubo_sa import qubo_sa_weights
from .vqe import vqe_weights
from .hybrid_pipeline import HybridPipelineInfo, hybrid_pipeline_weights

__all__ = [
    "equal_weight",
    "markowitz_max_sharpe",
    "min_variance",
    "target_return_frontier",
    "hrp_weights",
    "qubo_sa_weights",
    "vqe_weights",
    "hybrid_pipeline_weights",
]
