"""
Covariance estimation and risk metrics for portfolio optimization.

Provides:
- Ledoit-Wolf shrinkage covariance (drop-in replacement for sample covariance).
- Correlation extraction from covariance.
- Historical and parametric VaR / CVaR computation.
- ``build_risk_metrics_bundle`` — single call for the optimize response.

Reference:
  Ledoit & Wolf (2004), "A Well-Conditioned Estimator for Large-Dimensional
  Covariance Matrices", Journal of Multivariate Analysis 88(2), 365-411.
"""

import logging
import os
from typing import Dict, Optional

import numpy as np
from sklearn.covariance import LedoitWolf

logger = logging.getLogger(__name__)

# Environment flag to disable shrinkage (e.g. for A/B comparison).
_USE_LEDOIT_WOLF = os.getenv("USE_LEDOIT_WOLF", "true").lower() != "false"

# Minimum daily observations required to trust historical VaR.
_MIN_HIST_OBSERVATIONS = 30


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


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

def correlation_from_covariance(cov: np.ndarray) -> np.ndarray:
    """Derive an (N, N) correlation matrix from a covariance matrix.

    Diagonal elements are clamped to a small positive floor before
    normalisation so that zero-variance assets produce a row/column
    of zeros rather than NaN.
    """
    vols = np.sqrt(np.maximum(np.diag(cov), 1e-10))
    corr = cov / np.outer(vols, vols)
    np.fill_diagonal(corr, 1.0)
    return corr


# ---------------------------------------------------------------------------
# VaR / CVaR helpers — all operate on a 1-D array of *daily* portfolio returns
# ---------------------------------------------------------------------------

def portfolio_daily_returns(
    weights: np.ndarray,
    daily_returns: np.ndarray,
) -> np.ndarray:
    """Compute daily portfolio returns from weights and a (T, N) return panel.

    Returns a 1-D array of shape (T,).
    """
    return daily_returns @ weights


def var_historical_daily(
    portfolio_returns: np.ndarray,
    alpha: float = 0.05,
) -> float:
    """Historical simulation VaR at the given confidence level.

    Sign convention: *negative* values denote losses, matching the
    parametric ``-z * sigma`` convention used in the optimize response.
    The returned value is the ``alpha`` quantile of the return distribution,
    so a typical result is a small negative number (e.g. -0.018 = -1.8 %
    daily loss).
    """
    return float(np.percentile(portfolio_returns, alpha * 100))


def cvar_historical_daily(
    portfolio_returns: np.ndarray,
    alpha: float = 0.05,
) -> float:
    """Conditional VaR (Expected Shortfall) — mean of returns at or below VaR.

    Always at least as severe as VaR in loss magnitude.
    """
    var = var_historical_daily(portfolio_returns, alpha)
    tail = portfolio_returns[portfolio_returns <= var]
    if len(tail) == 0:
        return var
    return float(tail.mean())


# ---------------------------------------------------------------------------
# Bundle builder — single entry-point for the optimize response
# ---------------------------------------------------------------------------

def build_risk_metrics_bundle(
    portfolio_volatility: float,
    weights: np.ndarray,
    daily_returns: Optional[np.ndarray] = None,
    trading_days: int = 252,
    has_empirical_cov: bool = True,
) -> Dict:
    """Build backward-compatible ``risk_metrics`` dict for the API response.

    Parametric VaR/CVaR are always present (from annualized portfolio
    volatility).  Historical metrics are added only when a daily return
    panel is available and has at least ``_MIN_HIST_OBSERVATIONS`` rows.

    Backward-compat keys:
      ``var_95``  → alias for ``var_95_parametric``
      ``cvar``    → alias for ``cvar_95_parametric``

    These keep the Next.js dashboard and ``reportExport.ts`` working
    without frontend changes.
    """
    # --- parametric (normal assumption, one-day horizon) ---
    daily_vol = portfolio_volatility / (trading_days ** 0.5)
    var_95_param = -1.645 * daily_vol
    cvar_95_param = -2.063 * daily_vol

    metrics: Dict = {
        "var_95_parametric": round(var_95_param, 6),
        "cvar_95_parametric": round(cvar_95_param, 6),
        # backward-compat aliases
        "var_95": round(var_95_param, 6),
        "cvar": round(cvar_95_param, 6),
    }

    # --- historical (from daily return panel) ---
    if daily_returns is not None and len(daily_returns) >= _MIN_HIST_OBSERVATIONS:
        port_ret = portfolio_daily_returns(weights, daily_returns)
        var_hist = var_historical_daily(port_ret)
        cvar_hist = cvar_historical_daily(port_ret)
        metrics["var_95_historical"] = round(var_hist, 6)
        metrics["cvar_95"] = round(cvar_hist, 6)

    # --- provenance ---
    if has_empirical_cov:
        metrics["correlation_source"] = "empirical"
    elif daily_returns is not None:
        metrics["correlation_source"] = "matrix_with_panel"
    else:
        metrics["correlation_source"] = "matrix_no_panel"

    return metrics
