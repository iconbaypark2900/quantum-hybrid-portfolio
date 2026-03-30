"""
Hierarchical Risk Parity (HRP) — López de Prado.

Implements the full HRP pipeline:
  1. Correlation-based distance matrix.
  2. Hierarchical (single-linkage) clustering.
  3. Quasi-diagonalization (seriation via dendrogram leaf order).
  4. Recursive bisection with inverse-variance allocation.

Reference:
  López de Prado, M. (2016), "Building Diversified Portfolios that
  Outperform Out-of-Sample", SSRN 2708678.
"""

from typing import List

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hrp_weights(covariance: np.ndarray) -> np.ndarray:
    """
    Compute HRP portfolio weights from a covariance matrix.

    Args:
        covariance: (N, N) positive-semidefinite covariance matrix.

    Returns:
        (N,) array of portfolio weights summing to 1.
    """
    n = covariance.shape[0]
    if n == 1:
        return np.array([1.0])

    corr, vols = _cov_to_corr(covariance)
    dist = _correlation_distance(corr)
    link = _cluster(dist)
    order = list(leaves_list(link))
    weights = _recursive_bisection(covariance, order)
    return weights


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cov_to_corr(cov: np.ndarray):
    """Return (correlation_matrix, volatilities) from a covariance matrix."""
    vols = np.sqrt(np.diag(cov))
    vols_safe = np.where(vols > 0, vols, 1e-10)
    corr = cov / np.outer(vols_safe, vols_safe)
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1.0, 1.0)
    return corr, vols


def _correlation_distance(corr: np.ndarray) -> np.ndarray:
    """
    Convert a correlation matrix to a proper distance matrix.

    d_{ij} = sqrt(0.5 * (1 - rho_{ij}))
    """
    dist = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(dist, 0.0)
    return dist


def _cluster(dist: np.ndarray) -> np.ndarray:
    """
    Hierarchical single-linkage clustering on a distance matrix.

    Returns the linkage matrix (scipy format).
    """
    condensed = squareform(dist, checks=False)
    return linkage(condensed, method="single")


def _recursive_bisection(cov: np.ndarray, order: List[int]) -> np.ndarray:
    """
    Recursive bisection allocation (top-down) on the clustered asset order.

    Each split allocates between two sub-clusters using the inverse of
    each cluster's variance (computed with inverse-variance weights inside
    the cluster).
    """
    n = cov.shape[0]
    weights = np.ones(n)

    cluster_items: List[List[int]] = [order]

    while cluster_items:
        next_round: List[List[int]] = []
        for items in cluster_items:
            if len(items) <= 1:
                continue
            mid = len(items) // 2
            left = items[:mid]
            right = items[mid:]

            var_left = _cluster_variance(cov, left)
            var_right = _cluster_variance(cov, right)

            # Inverse-variance allocation between the two halves
            total_inv = 1.0 / var_left + 1.0 / var_right
            alpha_left = (1.0 / var_left) / total_inv
            alpha_right = 1.0 - alpha_left

            for idx in left:
                weights[idx] *= alpha_left
            for idx in right:
                weights[idx] *= alpha_right

            if len(left) > 1:
                next_round.append(left)
            if len(right) > 1:
                next_round.append(right)

        cluster_items = next_round

    weights = weights / weights.sum()
    return weights


def _cluster_variance(cov: np.ndarray, indices: List[int]) -> float:
    """
    Compute the variance of a cluster using inverse-variance weights.

    w_i = (1 / sigma_i^2) / sum(1 / sigma_j^2)  for j in cluster
    V_cluster = w' Sigma w
    """
    sub_cov = cov[np.ix_(indices, indices)]
    diag = np.diag(sub_cov)
    inv_var = 1.0 / np.maximum(diag, 1e-10)
    w = inv_var / inv_var.sum()
    return float(w @ sub_cov @ w)
