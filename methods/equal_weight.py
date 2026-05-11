"""
Equal Weight (1/N) portfolio — benchmark baseline.
"""

from typing import Optional

import numpy as np


def equal_weight(
    mu: np.ndarray,
    Sigma: np.ndarray,
    k_select: Optional[int] = None,
) -> np.ndarray:
    """
    Equal-weight (1/N) portfolio allocation.

    Parameters
    ----------
    mu : ndarray (n,)
        Expected annualised returns. Used only for top-k selection when
        k_select is set.
    Sigma : ndarray (n, n)
        Covariance matrix. Unused but kept for consistent signature.
    k_select : int, optional
        If set and < n, select the top-k assets by expected return and
        equal-weight only those. Others receive zero weight.

    Returns
    -------
    weights : ndarray (n,)
        Portfolio weights summing to 1.
    """
    n = len(mu)

    if k_select is not None and 0 < k_select < n:
        top_k_idx = np.argsort(mu)[::-1][:k_select]
        w = np.zeros(n)
        w[top_k_idx] = 1.0 / k_select
        return w

    return np.ones(n) / n
