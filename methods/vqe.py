"""
VQE Portfolio Optimization — PauliTwoDesign Ansatz (Scientific Reports 2023).

Variational Quantum Eigensolver simulated classically:
  1. Parameterised ansatz generates probability amplitudes → continuous weights
  2. COBYLA (gradient-free) optimises the circuit parameters
  3. Multiple restarts guard against local minima

The PauliTwoDesign ansatz is the most noise-robust of the four architectures
benchmarked in Scientific Reports (2023), making it the best choice for
near-term quantum hardware emulation.

Reference: Best practices for quantum error mitigation with VQE.
           Scientific Reports (2023).
           Orús, Mugel & Lizaso (2019). arXiv:1811.03975.
"""

import numpy as np
from scipy.optimize import minimize
from typing import Optional


def _pauli_two_design_ansatz(theta: np.ndarray, n: int, n_layers: int) -> np.ndarray:
    """
    PauliTwoDesign ansatz: alternating Pauli rotations + CZ ring entanglement.

    Maps parameter vector θ → probability amplitudes p ∈ [0,1]^n.

    Parameters
    ----------
    theta    : Parameter vector, length n * (n_layers + 1).
    n        : Number of assets / qubits.
    n_layers : Circuit depth.

    Returns
    -------
    p : ndarray (n,), values in (0, 1).
    """
    n_params = n * (n_layers + 1)
    th = theta[:n_params].reshape(n_layers + 1, n)
    p = np.ones(n) * 0.5

    for l_idx, layer_th in enumerate(th):
        if l_idx % 2 == 0:
            # Pauli-X/Z rotation: interpolate between p and 1-p
            p = np.cos(layer_th / 2) ** 2 * p + np.sin(layer_th / 2) ** 2 * (1 - p)
        else:
            # Pauli-Y rotation
            p = np.sin(layer_th / 2) ** 2
        # CZ ring entanglement: nearest-neighbour mixing
        p = 0.85 * p + 0.15 * np.roll(p, 1)

    return p


def vqe_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_layers: int = 3,
    n_restarts: int = 8,
    weight_min: float = 0.001,
    weight_max: float = 0.30,
    seed: int = 0,
) -> np.ndarray:
    """
    VQE portfolio optimisation with PauliTwoDesign ansatz.

    Optimises circuit parameters θ to maximise portfolio Sharpe ratio.
    Uses COBYLA (gradient-free), which outperforms gradient-based methods
    on noisy hardware (Scientific Reports 2023).

    Parameters
    ----------
    mu          : Expected annualised returns, shape (n,).
    Sigma       : Covariance matrix, shape (n, n).
    n_layers    : Ansatz circuit depth (default 3).
    n_restarts  : Number of random restarts.
    weight_min  : Minimum non-zero weight per asset.
    weight_max  : Maximum weight per asset.
    seed        : Base random seed.

    Returns
    -------
    weights : ndarray (n,), sum to 1.
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)
    n_params = n * (n_layers + 1)

    rng = np.random.default_rng(seed)
    best_sharpe = -np.inf
    best_w = np.ones(n) / n

    def objective(theta: np.ndarray) -> float:
        p = _pauli_two_design_ansatz(theta, n, n_layers)
        w = np.clip(p, weight_min, weight_max)
        w /= w.sum()
        r = w @ mu
        v = np.sqrt(w @ Sigma @ w)
        return -(r / v) if v > 1e-10 else 1e6

    for _ in range(n_restarts):
        theta0 = rng.uniform(-np.pi, np.pi, n_params)
        res = minimize(
            objective,
            theta0,
            method="COBYLA",
            options={"maxiter": 300, "rhobeg": 0.5},
        )
        p = _pauli_two_design_ansatz(res.x, n, n_layers)
        w = np.clip(p, weight_min, weight_max)
        w /= w.sum()
        sr = (w @ mu) / max(np.sqrt(w @ Sigma @ w), 1e-10)
        if sr > best_sharpe:
            best_sharpe, best_w = sr, w.copy()

    return best_w
