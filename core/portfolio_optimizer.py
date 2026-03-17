"""
Unified portfolio optimisation service.

Routes by `objective` parameter to one of six methods:

  equal_weight   : 1/N baseline
  markowitz      : Markowitz Max-Sharpe via SLSQP
  min_variance   : Global Minimum Variance
  hrp            : Hierarchical Risk Parity (López de Prado 2016)
  qubo_sa        : QUBO + Simulated Annealing (Orús et al. 2019)
  vqe            : VQE PauliTwoDesign (Scientific Reports 2023)
  hybrid         : 3-Stage Hybrid Pipeline (Buonaiuto/Herman 2025)
  target_return  : Efficient frontier point at a specific return target

All methods accept (mu, Sigma) in annualised units and return an
OptimizationResult with a uniform fields contract.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from core.optimizers.equal_weight import equal_weight
from core.optimizers.markowitz import markowitz_max_sharpe, min_variance, target_return_frontier
from core.optimizers.hrp import hrp_weights
from core.optimizers.qubo_sa import qubo_sa_weights
from core.optimizers.vqe import vqe_weights
from core.optimizers.hybrid_pipeline import hybrid_pipeline_weights


# ── Valid objectives ────────────────────────────────────────────────────────

OBJECTIVES = {
    "equal_weight":  "Equal Weight (1/N) — baseline",
    "markowitz":     "Markowitz Max-Sharpe (Markowitz 1952)",
    "min_variance":  "Global Minimum Variance",
    "hrp":           "Hierarchical Risk Parity (López de Prado 2016)",
    "qubo_sa":       "QUBO + Simulated Annealing (Orús et al. 2019)",
    "vqe":           "VQE PauliTwoDesign (Scientific Reports 2023)",
    "hybrid":        "3-Stage Hybrid Pipeline (Buonaiuto/Herman 2025)",
    "target_return": "Minimum-variance at target return",
}


# ── Result dataclass ────────────────────────────────────────────────────────

@dataclass
class OptimizationResult:
    """Uniform result contract for all optimisation methods."""
    weights: np.ndarray
    objective: str
    sharpe_ratio: float
    expected_return: float
    volatility: float
    n_active: int
    # Optional richer diagnostics
    asset_names: Optional[List[str]] = None
    stage_info: Optional[Dict] = None   # populated by hybrid pipeline


# ── Portfolio metric helpers ────────────────────────────────────────────────

def _portfolio_metrics(w: np.ndarray, mu: np.ndarray, Sigma: np.ndarray, rf: float = 0.0) -> Dict:
    r = float(w @ mu)
    v = float(np.sqrt(w @ Sigma @ w))
    sr = (r - rf) / v if v > 1e-10 else 0.0
    n_active = int(np.sum(w > 1e-4))
    return {"return": r, "volatility": v, "sharpe": sr, "n_active": n_active}


# ── Main entry point ────────────────────────────────────────────────────────

def run_optimization(
    returns: np.ndarray,
    covariance: np.ndarray,
    objective: str = "hybrid",
    target_return: Optional[float] = None,
    asset_names: Optional[List[str]] = None,
    # QUBO / Hybrid parameters
    K: Optional[int] = None,
    K_screen: Optional[int] = None,
    K_select: Optional[int] = None,
    lambda_risk: float = 1.0,
    gamma: float = 8.0,
    # VQE parameters
    n_layers: int = 3,
    n_restarts: int = 8,
    # Weight bounds
    weight_min: float = 0.005,
    weight_max: float = 0.30,
    # Reproducibility
    seed: int = 42,
) -> OptimizationResult:
    """
    Run portfolio optimisation with the specified objective.

    Parameters
    ----------
    returns     : Expected annualised returns, shape (n,).
    covariance  : Annualised covariance matrix, shape (n, n).
    objective   : One of the keys in OBJECTIVES dict.
    target_return : Required for 'target_return' objective.
    asset_names : Optional ticker list, stored in result.
    K           : Cardinality for qubo_sa (assets to select).
    K_screen    : Stage 1 screening size for hybrid.
    K_select    : Stage 2 selection size for hybrid.
    lambda_risk : QUBO risk-aversion coefficient.
    gamma       : QUBO cardinality penalty.
    n_layers    : VQE circuit depth.
    n_restarts  : VQE random restarts.
    weight_min  : Minimum weight per asset (for Markowitz and Hybrid Stage 3).
    weight_max  : Maximum weight per asset.
    seed        : Random seed.

    Returns
    -------
    OptimizationResult
    """
    mu = np.asarray(returns, dtype=float)
    Sigma = np.asarray(covariance, dtype=float)
    bounds = (weight_min, weight_max)

    if objective not in OBJECTIVES:
        raise ValueError(
            f"Unknown objective '{objective}'. "
            f"Valid options: {list(OBJECTIVES.keys())}"
        )

    stage_info = None

    # ── Dispatch ────────────────────────────────────────────────────────────
    if objective == "equal_weight":
        w = equal_weight(mu, Sigma)

    elif objective == "markowitz":
        w = markowitz_max_sharpe(mu, Sigma, weight_bounds=bounds, n_restarts=n_restarts)

    elif objective == "min_variance":
        w = min_variance(mu, Sigma, weight_bounds=bounds)

    elif objective == "hrp":
        w = hrp_weights(mu, Sigma)

    elif objective == "qubo_sa":
        w = qubo_sa_weights(
            mu, Sigma,
            K=K,
            lambda_risk=lambda_risk,
            gamma=gamma,
            seed=seed,
        )

    elif objective == "vqe":
        w = vqe_weights(
            mu, Sigma,
            n_layers=n_layers,
            n_restarts=n_restarts,
            weight_min=weight_min,
            weight_max=weight_max,
            seed=seed,
        )

    elif objective == "hybrid":
        w, info = hybrid_pipeline_weights(
            mu, Sigma,
            K_screen=K_screen,
            K_select=K_select,
            lambda_risk=lambda_risk,
            gamma=gamma,
            weight_bounds=bounds,
            seed=seed,
        )
        stage_info = {
            "stage1_screened_count": len(info.stage1_screened_idx),
            "stage2_selected_idx": info.stage2_selected_idx,
            "stage2_selected_names": (
                [asset_names[i] for i in info.stage2_selected_idx]
                if asset_names else info.stage2_selected_idx
            ),
            "stage2_qubo_obj": info.stage2_qubo_obj,
            "stage3_sharpe": info.stage3_sharpe,
            "stage1_ic": info.stage1_ic.tolist(),
        }

    elif objective == "target_return":
        if target_return is None:
            raise ValueError("'target_return' objective requires a target_return value.")
        # Find the frontier point closest to the requested return
        frontier = target_return_frontier(mu, Sigma, n_points=50, weight_bounds=(0.0, 1.0))
        if not frontier:
            w = np.ones(len(mu)) / len(mu)
        else:
            closest = min(frontier, key=lambda pt: abs(pt["target_return"] - target_return))
            w = np.asarray(closest["weights"])

    else:
        w = equal_weight(mu, Sigma)  # unreachable, but safe fallback

    # ── Compute metrics ─────────────────────────────────────────────────────
    metrics = _portfolio_metrics(w, mu, Sigma)

    return OptimizationResult(
        weights=w,
        objective=objective,
        sharpe_ratio=metrics["sharpe"],
        expected_return=metrics["return"],
        volatility=metrics["volatility"],
        n_active=metrics["n_active"],
        asset_names=asset_names,
        stage_info=stage_info,
    )


# ── Efficient frontier helper (unchanged contract) ──────────────────────────

def compute_efficient_frontier(
    returns: np.ndarray,
    covariance: np.ndarray,
    n_points: int = 30,
) -> List[Dict]:
    """
    Compute efficient frontier using Markowitz minimum-variance at target returns.

    Returns a list of dicts compatible with the existing API response shape:
    [{"target_return", "volatility", "sharpe", "weights"}, ...]
    """
    mu = np.asarray(returns, dtype=float)
    Sigma = np.asarray(covariance, dtype=float)
    return target_return_frontier(mu, Sigma, n_points=n_points)
