"""
Covariance estimation models for portfolio optimization.

Provides Ledoit-Wolf shrinkage covariance as a drop-in replacement for the
raw sample covariance, improving out-of-sample stability for all downstream
optimizers (max_sharpe / QSW, min_variance, risk_parity, target_return, HRP).

Reference:
  Ledoit & Wolf (2004), "A Well-Conditioned Estimator for Large-Dimensional
  Covariance Matrices", Journal of Multivariate Analysis 88(2), 365-411.
"""

import logging
import os

import numpy as np
from sklearn.covariance import LedoitWolf

logger = logging.getLogger(__name__)

# Environment flag to disable shrinkage (e.g. for A/B comparison).
_USE_LEDOIT_WOLF = os.getenv("USE_LEDOIT_WOLF", "true").lower() != "false"


def ledoit_wolf_covariance(
    returns: np.ndarray,
    annualize: bool = True,
    trading_days: int = 252,
) -> np.ndarray:
    """
    Compute the Ledoit-Wolf shrinkage covariance from a returns matrix.

    Args:
        returns: Shape (T, N) array of periodic (e.g. daily) returns.
        annualize: If True, multiply by *trading_days* to annualize.
        trading_days: Number of trading days per year (default 252).

    Returns:
        (N, N) shrunk covariance matrix (annualized if requested).
    """
    if not _USE_LEDOIT_WOLF:
        cov = np.cov(returns, rowvar=False)
        if annualize:
            cov = cov * trading_days
        return cov

    estimator = LedoitWolf().fit(returns)
    cov = estimator.covariance_
    shrinkage = estimator.shrinkage_

    logger.debug(
        "Ledoit-Wolf shrinkage coefficient: %.4f (N=%d, T=%d)",
        shrinkage,
        returns.shape[1],
        returns.shape[0],
    )

    if annualize:
        cov = cov * trading_days

    return cov
