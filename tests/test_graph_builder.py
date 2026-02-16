"""
Tests for core/quantum_inspired/graph_builder.py — FinancialGraphBuilder.

Covers graph structure, node/edge attributes, adaptive threshold, metrics,
and edge cases (identity covariance, perfect correlation).
"""
import sys
from pathlib import Path
import warnings

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pytest

from core.quantum_inspired.graph_builder import FinancialGraphBuilder
from config.qsw_config import QSWConfig


# --- Helpers ---

def _make_data(n: int = 6, seed: int = 42):
    """Return (returns, covariance) with a valid PSD covariance."""
    np.random.seed(seed)
    returns = np.random.randn(n) * 0.1 + 0.08
    A = np.random.randn(n, n)
    cov = A.T @ A / n + np.eye(n) * 0.01
    return returns.astype(float), cov.astype(float)


# ============================================================================
# Graph structure
# ============================================================================

class TestGraphStructure:

    def test_node_count_matches_assets(self):
        returns, cov = _make_data(8)
        builder = FinancialGraphBuilder()
        G, _ = builder.build_graph(returns, cov)
        assert G.number_of_nodes() == 8

    def test_graph_is_undirected(self):
        returns, cov = _make_data(5)
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        assert not G.is_directed()

    def test_no_self_loops(self):
        returns, cov = _make_data(6)
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        import networkx as nx
        assert nx.number_of_selfloops(G) == 0

    def test_edge_weights_positive(self):
        returns, cov = _make_data(6)
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        for u, v, data in G.edges(data=True):
            assert data['weight'] > 0, f"Edge ({u},{v}) has non-positive weight"


# ============================================================================
# Node attributes
# ============================================================================

class TestNodeAttributes:

    def test_node_has_return_potential(self):
        returns, cov = _make_data(4)
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        for i in range(4):
            assert 'return_potential' in G.nodes[i]
            assert np.isclose(G.nodes[i]['return_potential'], returns[i])

    def test_node_has_risk(self):
        returns, cov = _make_data(4)
        std_dev = np.sqrt(np.diag(cov))
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        for i in range(4):
            assert 'risk' in G.nodes[i]
            assert np.isclose(G.nodes[i]['risk'], std_dev[i])

    def test_node_has_sharpe(self):
        returns, cov = _make_data(4)
        std_dev = np.sqrt(np.diag(cov))
        G, _ = FinancialGraphBuilder().build_graph(returns, cov)
        for i in range(4):
            expected = returns[i] / std_dev[i] if std_dev[i] > 0 else 0
            assert np.isclose(G.nodes[i]['sharpe'], expected)


# ============================================================================
# Metrics dictionary
# ============================================================================

class TestMetrics:

    def test_metrics_keys_present(self):
        returns, cov = _make_data(6)
        _, metrics = FinancialGraphBuilder().build_graph(returns, cov)
        required = [
            'n_nodes', 'n_edges', 'density', 'threshold_used',
            'avg_weight', 'regime',
        ]
        for key in required:
            assert key in metrics, f"Missing metric key: {key}"

    def test_metrics_values_types(self):
        returns, cov = _make_data(6)
        _, metrics = FinancialGraphBuilder().build_graph(returns, cov)
        assert isinstance(metrics['n_nodes'], int)
        assert isinstance(metrics['n_edges'], int)
        assert isinstance(metrics['density'], float)
        assert isinstance(metrics['regime'], str)

    def test_density_range(self):
        returns, cov = _make_data(6)
        _, metrics = FinancialGraphBuilder().build_graph(returns, cov)
        assert 0.0 <= metrics['density'] <= 1.0


# ============================================================================
# Adaptive threshold / regimes
# ============================================================================

class TestAdaptiveThreshold:

    def test_volatile_regime_denser_than_bull(self):
        """Volatile regime uses lower threshold -> more edges than bull."""
        returns, cov = _make_data(10, seed=7)
        builder = FinancialGraphBuilder()
        _, m_volatile = builder.build_graph(returns, cov, market_regime='volatile')
        _, m_bull = builder.build_graph(returns, cov, market_regime='bull')
        assert m_volatile['n_edges'] >= m_bull['n_edges']

    def test_regime_stored_in_metrics(self):
        returns, cov = _make_data(5)
        _, m = FinancialGraphBuilder().build_graph(returns, cov, market_regime='bear')
        assert m['regime'] == 'bear'


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:

    def test_identity_covariance_no_edges(self):
        """Identity covariance -> zero off-diagonal correlation -> no edges."""
        n = 5
        returns = np.full(n, 0.05)
        cov = np.eye(n) * 0.04
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            G, metrics = FinancialGraphBuilder().build_graph(returns, cov)
            assert metrics['n_edges'] == 0
            assert any("no edges" in str(warning.message).lower() for warning in w)

    def test_perfect_correlation_fully_connected(self):
        """All correlations = 1 -> complete graph (or near-complete)."""
        n = 5
        vols = np.full(n, 0.2)
        cov = np.outer(vols, vols)  # perfect positive correlation
        returns = np.full(n, 0.10)
        G, metrics = FinancialGraphBuilder().build_graph(returns, cov)
        max_edges = n * (n - 1) // 2
        assert metrics['n_edges'] == max_edges, (
            f"Expected fully connected ({max_edges} edges), got {metrics['n_edges']}"
        )
