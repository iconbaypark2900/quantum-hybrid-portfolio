"""
Markowitz mean-variance optimization (Markowitz 1952).

Implements:
- markowitz_max_sharpe   : Maximum Sharpe Ratio via SLSQP
- min_variance           : Global Minimum Variance
- target_return_frontier : Efficient frontier points for a given return target
"""

from typing import Dict, List
import numpy as np
from scipy.optimize import minimize


def markowitz_max_sharpe(
    mu: np.ndarray,
    Sigma: np.ndarray,
    rf: float = 0.0,
    weight_bounds: tuple = (0.005, 0.30),
    n_restarts: int = 5,
) -> np.ndarray:
    """
    Maximum Sharpe Ratio portfolio via SLSQP.

    Solves:
        max  (w·μ - rf) / sqrt(w·Σ·w)
        s.t. sum(w) = 1,  w_i ∈ [lb, ub]

    Parameters
    ----------
    mu            : Expected annualised returns, shape (n,).
    Sigma         : Covariance matrix, shape (n, n).
    rf            : Risk-free rate (default 0).
    weight_bounds : (lower, upper) per-asset weight bounds.
    n_restarts    : Number of random starting points.

    Returns
    -------
    weights : ndarray (n,)
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    def neg_sharpe(w):
        r = w @ mu
        v = np.sqrt(w @ Sigma @ w)
        return -(r - rf) / v if v > 1e-10 else 1e10

    best_w = np.ones(n) / n
    best_sr = -np.inf

    for seed in range(n_restarts):
        rng = np.random.default_rng(seed)
        w0 = rng.dirichlet(np.ones(n))
        res = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=[weight_bounds] * n,
            constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
            options={"maxiter": 1000, "ftol": 1e-9},
        )
        if res.success:
            w = np.maximum(res.x, 0)
            w /= w.sum()
            sr = -neg_sharpe(w)
            if sr > best_sr:
                best_sr, best_w = sr, w.copy()

    return best_w


def min_variance(
    mu: np.ndarray,
    Sigma: np.ndarray,
    weight_bounds: tuple = (0.005, 0.30),
) -> np.ndarray:
    """
    Global Minimum Variance portfolio.

    Solves:
        min  w·Σ·w
        s.t. sum(w) = 1,  w_i ∈ [lb, ub]

    Parameters
    ----------
    mu            : Expected returns (unused, kept for uniform signature).
    Sigma         : Covariance matrix, shape (n, n).
    weight_bounds : (lower, upper) per-asset weight bounds.

    Returns
    -------
    weights : ndarray (n,)
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    def portfolio_variance(w):
        return w @ Sigma @ w

    w0 = np.ones(n) / n
    res = minimize(
        portfolio_variance,
        w0,
        method="SLSQP",
        bounds=[weight_bounds] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"maxiter": 1000, "ftol": 1e-9},
    )

    if res.success:
        w = np.maximum(res.x, 0)
        return w / w.sum()

    # Fallback: equal weight
    return np.ones(n) / n


def target_return_frontier(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_points: int = 30,
    weight_bounds: tuple = (0.0, 1.0),
) -> List[Dict]:
    """
    Compute efficient frontier by solving minimum-variance portfolios
    at a grid of target returns.

    Parameters
    ----------
    mu            : Expected returns, shape (n,).
    Sigma         : Covariance matrix, shape (n, n).
    n_points      : Number of frontier points.
    weight_bounds : (lower, upper) per-asset weight bounds.

    Returns
    -------
    List of dicts: [{"target_return", "volatility", "sharpe", "weights"}, ...]
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    # Anchor min-return at global min-variance portfolio
    res_mv = minimize(
        lambda w: w @ Sigma @ w,
        np.ones(n) / n,
        method="SLSQP",
        bounds=[weight_bounds] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"maxiter": 500},
    )
    min_ret = float(res_mv.x @ mu) if res_mv.success else float(np.min(mu))
    max_ret = float(np.max(mu))

    target_rets = np.linspace(min_ret, max_ret, n_points)
    frontier = []

    for tr in target_rets:
        res = minimize(
            lambda w: w @ Sigma @ w,
            np.ones(n) / n,
            method="SLSQP",
            bounds=[weight_bounds] * n,
            constraints=[
                {"type": "eq", "fun": lambda w: w.sum() - 1},
                {"type": "eq", "fun": lambda w, tr=tr: w @ mu - tr},
            ],
            options={"maxiter": 500, "ftol": 1e-9},
        )
        if res.success:
            w = np.maximum(res.x, 0)
            w /= w.sum()
            vol = float(np.sqrt(w @ Sigma @ w))
            ret = float(w @ mu)
            frontier.append(
                {
                    "target_return": float(tr),
                    "volatility": vol,
                    "sharpe": ret / vol if vol > 1e-10 else 0.0,
                    "weights": w.tolist(),
                }
            )

    return frontier
