"""
Cross-sectional 4-factor model for portfolio analysis.

Factors are derived entirely from the (mu, Sigma) inputs available at
optimization time — no external factor database or daily return time-series
required. All scores are z-scored across assets (mean=0, std=1).

Factors
-------
market_beta  : standardised annualised return (higher return ≈ higher beta proxy)
size         : negative of annualised volatility (lower vol ≈ "larger" proxy)
momentum     : same as market_beta cross-sectionally; noted limitation — a
               proper momentum signal requires a trailing-return time-series
               (parking lot: wire market_payload.daily_returns through
               run_optimization when available)
low_vol      : negative of annualised volatility (explicit low-volatility tilt)
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_factor_scores(
    mu: np.ndarray,
    sigma_diag: np.ndarray,
    asset_names: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return a ``(n_assets, 4)`` DataFrame of z-scored factor scores.

    Parameters
    ----------
    mu:
        Annualised mean return for each asset, shape ``(n_assets,)``.
    sigma_diag:
        Annualised variance for each asset (``np.diag(Sigma)``),
        shape ``(n_assets,)``.  Pass variances, not standard deviations —
        the function takes the square-root internally.
    asset_names:
        Optional list of ticker / asset names used as the DataFrame index.

    Returns
    -------
    pd.DataFrame with columns ``['market_beta', 'size', 'momentum', 'low_vol']``
    and one row per asset.  Each column is z-scored (mean≈0, std≈1).
    """
    mu = np.asarray(mu, dtype=float)
    sigma_diag = np.asarray(sigma_diag, dtype=float)
    n = len(mu)

    if n < 2:
        raise ValueError("compute_factor_scores requires at least 2 assets")
    if len(sigma_diag) != n:
        raise ValueError("mu and sigma_diag must have the same length")

    vols = np.sqrt(np.maximum(sigma_diag, 1e-12))

    raw = pd.DataFrame(
        {
            "market_beta": mu,
            "size": -vols,
            "momentum": mu,
            "low_vol": -vols,
        },
        index=asset_names if asset_names is not None else list(range(n)),
    )

    scores = (raw - raw.mean()) / (raw.std(ddof=0) + 1e-8)
    return scores


def compute_portfolio_factor_exposure(
    weights: np.ndarray,
    factor_scores: pd.DataFrame,
) -> dict[str, Any]:
    """Return weighted-average factor exposure of the portfolio.

    Parameters
    ----------
    weights:
        Portfolio weight vector aligned with ``factor_scores`` rows.
    factor_scores:
        Output of :func:`compute_factor_scores`.

    Returns
    -------
    dict with keys ``market_beta``, ``size``, ``momentum``, ``low_vol``.
    """
    weights = np.asarray(weights, dtype=float)
    if len(weights) != len(factor_scores):
        raise ValueError(
            f"weights length {len(weights)} != factor_scores rows {len(factor_scores)}"
        )
    exposure = factor_scores.values.T @ weights
    cols = list(factor_scores.columns)
    return {col: float(exposure[i]) for i, col in enumerate(cols)}


def factor_tilt_weights(
    weights: np.ndarray,
    factor_scores: pd.DataFrame,
    tilt_alpha: float = 0.10,
) -> np.ndarray:
    """Apply a mild factor tilt to existing weights.

    Blends ``weights`` toward a score-proportional allocation, slightly
    increasing allocation to assets with higher composite factor scores.
    The blend is conservative (``tilt_alpha=0.10``) so it does not
    dominate the primary optimizer signal.

    Parameters
    ----------
    weights:
        Current portfolio weights (sum to 1).
    factor_scores:
        Output of :func:`compute_factor_scores`.
    tilt_alpha:
        Blending coefficient in [0, 1].  0 = no change; 1 = pure tilt.

    Returns
    -------
    Re-normalised weight vector with the same shape as ``weights``.
    """
    weights = np.asarray(weights, dtype=float)
    composite = factor_scores.values.mean(axis=1)
    composite_shifted = composite - composite.min() + 1e-6
    tilt_target = composite_shifted / composite_shifted.sum()

    blended = (1.0 - tilt_alpha) * weights + tilt_alpha * tilt_target
    blended = np.maximum(blended, 0.0)
    total = blended.sum()
    if total < 1e-10:
        return weights
    return blended / total
