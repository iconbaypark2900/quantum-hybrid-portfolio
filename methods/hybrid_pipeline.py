"""
3-Stage Hybrid Quantum-Classical Portfolio Pipeline.

Two variants
------------
hybrid_pipeline_weights  (objective: hybrid)
    Stage 2 solver: QUBO + Simulated Annealing (CPU, any universe size).

hybrid_qaoa_weights  (objective: hybrid_qaoa)
    Stage 2 solver: QUBO + QAOA gate-model circuit.
    Classical path: numpy statevector (K_screen ≤ 12).
    IBM Quantum path: EstimatorV2 + SamplerV2 on Qiskit Runtime (K_screen ≤ 20).
    Stages 1 and 3 are identical to the SA variant.

Pipeline (both variants)
------------------------
  Stage 1 — Classical IC Screening
      Rank all n assets by Information Coefficient (IC = μ/σ).
      Keep top K_screen candidates.

  Stage 2 — Quantum Discrete Selection
      Build QUBO on the screened sub-universe.
      SA variant:   _run_sa selects K_select assets.
      QAOA variant: gate-model QAOA selects K_select assets.

  Stage 3 — Classical Continuous Allocation
      Run Markowitz Max-Sharpe on the K_select selected assets.

The quantum stage handles the *combinatorial* question (which assets?).
Classical stages handle screening efficiency and weight precision.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from .qubo_sa import _build_qubo_matrix, _run_sa

logger = logging.getLogger(__name__)


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
    logger.info("hybrid_stage1: screened n=%d -> K_screen=%d", n, K_screen)

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
    logger.info("hybrid_stage2: QUBO-SA selected K_select=%d, obj=%.4f", K_select, float(best_obj))

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

    logger.info("hybrid_stage3: Markowitz Sharpe=%.4f for %d assets", float(best_sr), n_sel)

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


# ── Hybrid-QAOA variant ──────────────────────────────────────────────────────

def hybrid_qaoa_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K_screen: Optional[int] = None,
    K_select: Optional[int] = None,
    p: int = 2,
    lambda_risk: float = 0.8,
    gamma: float = 6.0,
    n_qaoa_restarts: int = 4,
    weight_bounds: tuple = (0.005, 0.30),
    seed: int = 42,
    # IBM path (only used when ibm_service is provided)
    ibm_service=None,
    backend_name: Optional[str] = None,
    backend_mode: str = "auto",
) -> tuple:
    """
    3-Stage Hybrid Pipeline with QAOA stage 2 (Quantum Ledger variant).

    Identical to hybrid_pipeline_weights except Stage 2 replaces Simulated
    Annealing with a QAOA gate-model circuit over the same QUBO.

    Parameters
    ----------
    mu              : Expected annualised returns, shape (n,).
    Sigma           : Covariance matrix, shape (n, n).
    K_screen        : Assets retained after IC screening.
                      Classical path requires K_screen ≤ 12 (statevector cap).
                      IBM path allows K_screen ≤ 20.
                      Defaults to min(max(5, n // 2), 12).
    K_select        : Assets selected via QAOA. Defaults to max(3, K_screen // 2).
    p               : QAOA circuit depth (cost + mixer layers per layer).
    lambda_risk     : QUBO risk-aversion coefficient.
    gamma           : QUBO cardinality penalty.
    n_qaoa_restarts : COBYLA multi-start restarts for QAOA angle optimisation.
    weight_bounds   : (min, max) weight per selected asset in Stage 3.
    seed            : Random seed.
    ibm_service     : Optional live QiskitRuntimeService. When provided, stage 2
                      runs on IBM Quantum Runtime (EstimatorV2 + SamplerV2).
                      When None (default), uses classical numpy statevector.
    backend_name    : Specific IBM backend name (None = auto-select).
    backend_mode    : IBM backend preference: 'auto' | 'simulator' | 'hardware'.

    Returns
    -------
    w_full : ndarray (n,) — weights for all assets (0 for unselected).
    info   : HybridPipelineInfo — stage diagnostics.
    """
    from .qaoa import (
        _qubo_to_ising,
        _cost_energy_diagonal,
        _qaoa_statevector,
        _select_k_from_probs,
        MAX_SIM_QUBITS,
        MAX_IBM_QUBITS,
        _build_qaoa_circuit_qiskit,
        _qaoa_weights_ibm,
    )

    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    max_screen = MAX_IBM_QUBITS if ibm_service is not None else MAX_SIM_QUBITS

    if K_screen is None:
        K_screen = min(max(5, n // 2), max_screen)
    if K_select is None:
        K_select = max(3, K_screen // 2)

    K_screen = min(K_screen, n, max_screen)
    K_select = min(K_select, K_screen)

    if K_screen > max_screen:
        raise ValueError(
            f"K_screen={K_screen} exceeds the QAOA statevector cap "
            f"({max_screen} qubits). Reduce K_screen or use objective='hybrid' "
            f"(SA path has no qubit cap)."
        )

    # ── Stage 1: Classical IC screening ─────────────────────────────────────
    vols = np.sqrt(np.maximum(np.diag(Sigma), 1e-10))
    ic = mu / vols
    screened_idx = np.argsort(ic)[-K_screen:]
    logger.info("hybrid_qaoa_stage1: screened n=%d -> K_screen=%d", n, K_screen)

    mu_s = mu[screened_idx]
    Sigma_s = Sigma[np.ix_(screened_idx, screened_idx)]

    # ── Stage 2: QAOA on screened sub-universe ───────────────────────────────
    Q = _build_qubo_matrix(mu_s, Sigma_s, K_select, lambda_risk, gamma)
    h, J = _qubo_to_ising(Q)

    if ibm_service is not None:
        # IBM Quantum Runtime path
        w_stage2, _qmeta = _qaoa_weights_ibm(
            mu=mu_s,
            Sigma=Sigma_s,
            K=K_select,
            p=p,
            lambda_risk=lambda_risk,
            gamma=gamma,
            n_restarts=n_qaoa_restarts,
            seed=seed,
            backend_name=backend_name,
            backend_mode=backend_mode,
        )
        selected_in_screen = np.where(w_stage2 > 1e-6)[0]
        stage2_obj = float(w_stage2[selected_in_screen] @ Q[np.ix_(selected_in_screen, selected_in_screen)] @ w_stage2[selected_in_screen])
        logger.info(
            "hybrid_qaoa_stage2 (IBM): K_select=%d selected=%d",
            K_select, len(selected_in_screen),
        )
    else:
        # Classical numpy statevector path
        n_s = len(mu_s)
        cost_diag = _cost_energy_diagonal(h, J, n_s)

        rng = np.random.default_rng(seed)
        best_energy = np.inf
        best_params: Optional[np.ndarray] = None

        def _energy(params: np.ndarray) -> float:
            state = _qaoa_statevector(n_s, p, params[:p], params[p:], cost_diag)
            return float((np.abs(state) ** 2) @ cost_diag)

        for _ in range(n_qaoa_restarts):
            theta0 = np.concatenate([
                rng.uniform(0.0, np.pi, p),
                rng.uniform(0.0, np.pi / 2, p),
            ])
            res = minimize(_energy, theta0, method="COBYLA",
                           options={"maxiter": 300, "rhobeg": 0.3})
            if res.fun < best_energy:
                best_energy = res.fun
                best_params = res.x

        if best_params is None:
            best_params = rng.uniform(0.0, np.pi, 2 * p)

        final_state = _qaoa_statevector(n_s, p, best_params[:p], best_params[p:], cost_diag)
        probs = np.abs(final_state) ** 2
        w_stage2 = _select_k_from_probs(probs, K_select, n_s)
        selected_in_screen = np.where(w_stage2 > 1e-6)[0]
        stage2_obj = best_energy
        logger.info(
            "hybrid_qaoa_stage2 (classical): K_select=%d energy=%.4f",
            K_select, best_energy,
        )

    selected_global = screened_idx[selected_in_screen]

    # ── Stage 3: Markowitz Max-Sharpe within selected assets ─────────────────
    n_sel = len(selected_global)
    if n_sel == 0:
        # Fallback: equal weight on all screened assets
        logger.warning("hybrid_qaoa_stage2: no assets selected, falling back to equal weight on screened")
        w_full = np.zeros(n)
        w_full[screened_idx] = 1.0 / len(screened_idx)
        info = HybridPipelineInfo(
            stage1_screened_idx=screened_idx.tolist(),
            stage1_ic=ic,
            stage2_selected_idx=[],
            stage2_qubo_obj=float(stage2_obj),
            stage3_sharpe=0.0,
        )
        return w_full, info

    mu_sel = mu[selected_global]
    Sigma_sel = Sigma[np.ix_(selected_global, selected_global)]

    def neg_sharpe(w):
        r = w @ mu_sel
        v = np.sqrt(w @ Sigma_sel @ w)
        return -(r / v) if v > 1e-10 else 1e10

    best_w_sel = np.ones(n_sel) / n_sel
    best_sr = -np.inf

    for s in range(5):
        rng2 = np.random.default_rng(seed + s + 200)
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

    logger.info(
        "hybrid_qaoa_stage3: Markowitz Sharpe=%.4f for %d assets",
        float(best_sr), n_sel,
    )

    w_full = np.zeros(n)
    w_full[selected_global] = best_w_sel

    info = HybridPipelineInfo(
        stage1_screened_idx=screened_idx.tolist(),
        stage1_ic=ic,
        stage2_selected_idx=selected_global.tolist(),
        stage2_qubo_obj=float(stage2_obj),
        stage3_sharpe=float(best_sr),
    )

    return w_full, info
