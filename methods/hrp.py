"""
Hierarchical Risk Parity (López de Prado 2016, Chapter 16).

Three-step algorithm:
  1. Hierarchical clustering on correlation distance matrix
  2. Quasi-diagonalization — sort leaves so correlated assets are adjacent
  3. Recursive bisection — allocate via inverse-variance within each cluster

Reference: López de Prado, M. (2016). Building Diversified Portfolios that
           Outperform Out-of-Sample. Journal of Portfolio Management.
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform


def hrp_weights(mu: np.ndarray, Sigma: np.ndarray = None) -> np.ndarray:
    """
    Hierarchical Risk Parity portfolio weights.

    Parameters
    ----------
    mu    : Expected returns, shape (n,), or covariance if Sigma is None. Unused.
    Sigma : Covariance matrix, shape (n, n). If None, mu is treated as Sigma.

    Returns
    -------
    weights : ndarray (n,), sum to 1.
    """
    if Sigma is None:
        Sigma = np.asarray(mu, dtype=float)
    else:
        Sigma = np.asarray(Sigma, dtype=float)
    n = Sigma.shape[0]

    # ── Step 1: Correlation distance matrix ────────────────────────────────
    std = np.sqrt(np.diag(Sigma))
    # Guard against zero-vol assets
    std = np.where(std < 1e-10, 1e-10, std)
    corr = Sigma / np.outer(std, std)
    corr = np.clip(corr, -1.0, 1.0)
    np.fill_diagonal(corr, 1.0)

    # Distance: d(i,j) = sqrt(0.5 * (1 - ρ_{ij}))
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, None))
    np.fill_diagonal(dist, 0.0)

    # ── Step 2: Hierarchical clustering → leaf ordering ────────────────────
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    sort_idx = list(leaves_list(link))

    # ── Step 3: Recursive bisection with inverse-variance allocation ────────
    import pandas as pd

    weights = pd.Series(1.0, index=range(n))
    clusters = [sort_idx]

    while clusters:
        # Split each cluster in half
        clusters = [
            sub[j:k]
            for sub in clusters
            for j, k in ((0, len(sub) // 2), (len(sub) // 2, len(sub)))
            if len(sub) > 1
        ]
        # Allocate between each adjacent pair
        for i in range(0, len(clusters), 2):
            if i + 1 >= len(clusters):
                break
            left, right = clusters[i], clusters[i + 1]

            def _cluster_var(idx_list):
                sub = Sigma[np.ix_(idx_list, idx_list)]
                iv = 1.0 / np.maximum(np.diag(sub), 1e-10)
                iv /= iv.sum()
                return float(iv @ sub @ iv)

            cv_l = _cluster_var(left)
            cv_r = _cluster_var(right)
            alloc_l = 1.0 - cv_l / (cv_l + cv_r + 1e-12)
            weights[left] *= alloc_l
            weights[right] *= 1.0 - alloc_l

    w = weights.values.astype(float)
    w = np.maximum(w, 0.0)
    return w / w.sum()
