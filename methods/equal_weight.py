"""
Equal Weight (1/N) portfolio — benchmark baseline.
"""

import numpy as np


def equal_weight(mu: np.ndarray, Sigma: np.ndarray) -> np.ndarray:
    """
    Equal-weight (1/N) portfolio allocation.

    Parameters
    ----------
    mu : ndarray (n,)
        Expected annualised returns. Unused but kept for consistent signature.
    Sigma : ndarray (n, n)
        Covariance matrix. Unused but kept for consistent signature.

    Returns
    -------
    weights : ndarray (n,)
        Portfolio weights summing to 1, all equal.
    """
    n = len(mu)
    return np.ones(n) / n
