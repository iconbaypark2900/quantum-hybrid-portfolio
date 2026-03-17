"""
3-Stage Hybrid Quantum-Classical Portfolio Pipeline.

Synthesises:
  - Buonaiuto et al. (2023 / Springer 2025): Best Practices for Portfolio
    Optimization by Quantum Computing — hybrid architecture design
  - Herman et al. (arXiv 2025): End-to-End Portfolio Optimization with
    Hybrid Quantum Annealing — workflow integration

Pipeline:
  Stage 1 — Classical screening
      Rank all n assets by Information Coefficient (IC = μ/σ).
      Keep top K_screen candidates.

  Stage 2 — Quantum discrete selection (QUBO + Simulated Annealing)
      Build QUBO on the screened sub-universe.
      SA selects exactly K_select assets.

  Stage 3 — Classical continuous allocation
      Run Markowitz Max-Sharpe on the K_select selected assets.
      Produces continuous weights with bounded exposure.

The quantum stage handles the *combinatorial* question (which assets?).
Classical stages handle screening efficiency and weight precision.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from scipy.optimize import minimize

from .qubo_sa import _build_qubo_matrix, _run_sa


@dataclass
class HybridPipelineInfo:
    """Diagnostic information from each stage of the hybrid pipeline."""
    stage1_screened_idx: List[int] = field(default_factory=list)
    stage1_ic: np.ndarray = field(default_factory=lambda: np.array([]))
    stage2_selected_idx: List[int] = field(default_factory=list)   # indices into full universe
    stage2_qubo_obj: float = 0.0
    stage3_sharpe: float = 0.0


def hybrid_pipeline_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K_screen: Optional[int] = None,
    K_select: Optional[int] = None,
    lambda_risk: float = 0.8,
    gamma: float = 6.0,
    n_sa_steps: int = 8000,
    n_sa_restarts: int = 20,
    weight_bounds: tuple = (0.005, 0.30),
    seed: int = 42,
) -> tuple:
    """
    3-Stage Hybrid Quantum-Classical Portfolio Optimisation.

    Parameters
    ----------
    mu            : Expected annualised returns, shape (n,).
    Sigma         : Covariance matrix, shape (n, n).
    K_screen      : Assets to keep after IC screening.
                    Defaults to min(max(5, n // 2), n).
    K_select      : Assets to select via QUBO.
                    Defaults to max(3, K_screen // 2).
    lambda_risk   : QUBO risk-aversion coefficient.
    gamma         : QUBO cardinality penalty.
    n_sa_steps    : SA steps per restart.
    n_sa_restarts : SA restarts.
    weight_bounds : (min, max) weight per selected asset.
    seed          : Random seed.

    Returns
    -------
    w_full : ndarray (n,) — weights for all assets (0 for unselected).
    info   : HybridPipelineInfo — diagnostics from each stage.
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    # Default cardinality parameters
    if K_screen is None:
        K_screen = min(max(5, n // 2), n)
    if K_select is None:
        K_select = max(3, K_screen // 2)

    K_screen = min(K_screen, n)
    K_select = min(K_select, K_screen)

    # ── Stage 1: Classical screening via IC = μ/σ ──────────────────────────
    vols = np.sqrt(np.maximum(np.diag(Sigma), 1e-10))
    ic = mu / vols  # Information Coefficient (Sharpe proxy per asset)
    screened_idx = np.argsort(ic)[-K_screen:]  # top K_screen by IC

    mu_s = mu[screened_idx]
    Sigma_s = Sigma[np.ix_(screened_idx, screened_idx)]

    # ── Stage 2: QUBO-SA on screened sub-universe ──────────────────────────
    Q = _build_qubo_matrix(mu_s, Sigma_s, K_select, lambda_risk, gamma)
    rng = np.random.default_rng(seed)

    best_x, best_obj = None, np.inf
    for _ in range(n_sa_restarts):
        x, obj = _run_sa(Q, K_select, n_sa_steps, T_start=15.0, T_end=0.001, rng=rng)
        if obj < best_obj:
            best_obj, best_x = obj, x.copy()

    # Map selected indices back to full universe
    selected_in_screen = np.where(best_x == 1)[0]
    selected_global = screened_idx[selected_in_screen]

    # ── Stage 3: Markowitz Max-Sharpe within selected assets ────────────────
    n_sel = len(selected_global)
    mu_sel = mu[selected_global]
    Sigma_sel = Sigma[np.ix_(selected_global, selected_global)]

    def neg_sharpe(w):
        r = w @ mu_sel
        v = np.sqrt(w @ Sigma_sel @ w)
        return -(r / v) if v > 1e-10 else 1e10

    best_w_sel = np.ones(n_sel) / n_sel
    best_sr = -np.inf

    for s in range(5):
        rng2 = np.random.default_rng(seed + s + 100)
        w0 = rng2.dirichlet(np.ones(n_sel))
        res = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=[weight_bounds] * n_sel,
            constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
            options={"maxiter": 500, "ftol": 1e-9},
        )
        if res.success:
            w = np.maximum(res.x, 0)
            w /= w.sum()
            sr = -neg_sharpe(w)
            if sr > best_sr:
                best_sr, best_w_sel = sr, w.copy()

    # Embed selected weights into full weight vector
    w_full = np.zeros(n)
    w_full[selected_global] = best_w_sel

    info = HybridPipelineInfo(
        stage1_screened_idx=screened_idx.tolist(),
        stage1_ic=ic,
        stage2_selected_idx=selected_global.tolist(),
        stage2_qubo_obj=float(best_obj),
        stage3_sharpe=float(best_sr),
    )

    return w_full, info
