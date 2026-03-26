"""
QUBO Portfolio Selection via Simulated Annealing (Orús et al. 2019).

Frames portfolio selection as a Quadratic Unconstrained Binary Optimization:

    min  x^T Q x
    s.t. sum(x) = K,  x_i ∈ {0, 1}

where:
    Q[i,i] = -μ_i + λ·Σ[i,i] + γ·(1 - 2K)
    Q[i,j] = λ·Σ[i,j] + γ         (i ≠ j)

Simulated Annealing acts as a classical proxy for D-Wave quantum annealing.
Constrained flips (swap one 0↔1 pair) maintain cardinality K throughout.

Reference: Orús, Mugel & Lizaso (2019). Quantum computing for finance:
           Overview and prospects. arXiv:1811.03975.
           Nature Reviews Physics 1, 586–600.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _build_qubo_matrix(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K: int,
    lambda_risk: float,
    gamma: float,
) -> np.ndarray:
    """Build the QUBO Q matrix from portfolio parameters."""
    n = len(mu)
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -mu[i] + lambda_risk * Sigma[i, i] + gamma * (1 - 2 * K)
        for j in range(i + 1, n):
            Q[i, j] = Q[j, i] = lambda_risk * Sigma[i, j] + gamma
    return Q


def _run_sa(
    Q: np.ndarray,
    K: int,
    n_steps: int,
    T_start: float,
    T_end: float,
    rng: np.random.Generator,
) -> tuple:
    """Single SA run. Returns (best_x, best_obj)."""
    n = Q.shape[0]
    x = np.zeros(n, dtype=int)
    x[rng.choice(n, K, replace=False)] = 1
    obj = float(x @ Q @ x)

    best_x = x.copy()
    best_obj = obj

    cool = (T_end / T_start) ** (1.0 / n_steps)
    T = T_start

    for _ in range(n_steps):
        ones = np.where(x == 1)[0]
        zeros = np.where(x == 0)[0]
        flip_out = rng.choice(ones)
        flip_in = rng.choice(zeros)

        x2 = x.copy()
        x2[flip_out] = 0
        x2[flip_in] = 1
        new_obj = float(x2 @ Q @ x2)

        delta = new_obj - obj
        if delta < 0 or rng.random() < np.exp(-delta / max(T, 1e-10)):
            x, obj = x2, new_obj
            if obj < best_obj:
                best_obj, best_x = obj, x.copy()

        T *= cool

    return best_x, best_obj


def qubo_sa_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K: Optional[int] = None,
    lambda_risk: float = 1.0,
    gamma: float = 8.0,
    n_steps: int = 8000,
    n_restarts: int = 20,
    T_start: float = 15.0,
    T_end: float = 0.001,
    seed: int = 42,
) -> np.ndarray:
    """
    QUBO portfolio selection via Simulated Annealing.

    Selects exactly K assets using QUBO+SA, then allocates equal weight
    within the selected subset.

    Parameters
    ----------
    mu          : Expected annualised returns, shape (n,).
    Sigma       : Covariance matrix, shape (n, n).
    K           : Number of assets to select. Defaults to max(2, n // 3).
    lambda_risk : Risk aversion coefficient in QUBO.
    gamma       : Cardinality penalty strength.
    n_steps     : SA steps per restart.
    n_restarts  : Number of independent SA runs.
    T_start     : Initial SA temperature.
    T_end       : Final SA temperature.
    seed        : Random seed for reproducibility.

    Returns
    -------
    weights : ndarray (n,), sum to 1.
              Selected assets get equal weight; unselected assets get 0.
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    if K is None:
        K = max(2, n // 3)
    K = min(K, n)

    Q = _build_qubo_matrix(mu, Sigma, K, lambda_risk, gamma)
    rng = np.random.default_rng(seed)

    best_x, best_obj = None, np.inf
    for _ in range(n_restarts):
        x, obj = _run_sa(Q, K, n_steps, T_start, T_end, rng)
        if obj < best_obj:
            best_obj, best_x = obj, x.copy()

    logger.info("qubo_sa: K=%d, n_assets=%d, restarts=%d, best_obj=%.4f", K, n, n_restarts, float(best_obj))
    w = np.zeros(n)
    selected = np.where(best_x == 1)[0]
    if len(selected) > 0:
        w[selected] = 1.0 / len(selected)

    return w
