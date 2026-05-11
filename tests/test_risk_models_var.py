"""
Tests for services.risk_models — correlation, historical VaR/CVaR,
and the risk_metrics bundle wired into the optimize endpoint.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pytest

from services.risk_models import (
    correlation_from_covariance,
    portfolio_daily_returns,
    var_historical_daily,
    cvar_historical_daily,
    build_risk_metrics_bundle,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_daily(seed=42, n_assets=5, n_days=252):
    """Multivariate-normal daily returns with known covariance."""
    rng = np.random.default_rng(seed)
    vols = np.array([0.01, 0.012, 0.015, 0.009, 0.02])
    corr = np.eye(n_assets) * 0.6 + 0.4
    np.fill_diagonal(corr, 1.0)
    cov = np.outer(vols, vols) * corr
    daily = rng.multivariate_normal(np.zeros(n_assets), cov, size=n_days)
    weights = np.ones(n_assets) / n_assets
    return daily, cov, weights


# ---------------------------------------------------------------------------
# 1. correlation_from_covariance
# ---------------------------------------------------------------------------

class TestCorrelationFromCovariance:
    def test_shape_and_symmetry(self, synthetic_daily):
        _, cov, _ = synthetic_daily
        corr = correlation_from_covariance(cov)
        assert corr.shape == cov.shape, "shape must match covariance"
        np.testing.assert_allclose(corr, corr.T, atol=1e-12, err_msg="must be symmetric")

    def test_diagonal_is_one(self, synthetic_daily):
        _, cov, _ = synthetic_daily
        corr = correlation_from_covariance(cov)
        np.testing.assert_allclose(np.diag(corr), 1.0, atol=1e-12)

    def test_off_diagonal_bounded(self, synthetic_daily):
        _, cov, _ = synthetic_daily
        corr = correlation_from_covariance(cov)
        off = corr[~np.eye(corr.shape[0], dtype=bool)]
        assert np.all(off >= -1.0 - 1e-10) and np.all(off <= 1.0 + 1e-10)

    def test_zero_variance_asset(self):
        """An asset with zero variance should produce a row/col of zeros, not NaN."""
        cov = np.array([[0.04, 0.01, 0.0],
                        [0.01, 0.09, 0.0],
                        [0.0,  0.0,  0.0]])
        corr = correlation_from_covariance(cov)
        assert not np.any(np.isnan(corr)), "NaN from zero-variance asset"
        np.testing.assert_allclose(corr[2, :2], 0.0, atol=1e-8)


# ---------------------------------------------------------------------------
# 2. Historical VaR vs parametric VaR
# ---------------------------------------------------------------------------

class TestVarHistoricalVsParametric:
    def test_within_tolerance(self, synthetic_daily):
        """On normally distributed data the empirical 5th-percentile daily VaR
        should be close to the parametric -1.645 * sigma estimate. We allow
        20 % relative tolerance because the sample is finite."""
        daily, cov, weights = synthetic_daily
        port_ret = portfolio_daily_returns(weights, daily)
        hist = var_historical_daily(port_ret)

        port_vol = float(np.sqrt(weights @ cov @ weights))
        parametric = -1.645 * port_vol

        # Both values should be negative (loss)
        assert hist < 0, "VaR must be negative (loss direction)"
        assert parametric < 0
        np.testing.assert_allclose(
            hist, parametric, rtol=0.20,
            err_msg="Empirical and parametric VaR should be within 20%",
        )


# ---------------------------------------------------------------------------
# 3. CVaR >= VaR (in loss magnitude)
# ---------------------------------------------------------------------------

class TestCvarExceedsVar:
    def test_cvar_more_severe(self, synthetic_daily):
        """CVaR must always be at least as severe as VaR (further into the tail)."""
        daily, _, weights = synthetic_daily
        port_ret = portfolio_daily_returns(weights, daily)
        var = var_historical_daily(port_ret)
        cvar = cvar_historical_daily(port_ret)
        assert cvar <= var, (
            f"CVaR ({cvar}) must be <= VaR ({var}) since both are negative "
            "and CVaR averages deeper into the loss tail"
        )

    def test_identical_returns(self):
        """When all daily returns are identical CVaR == VaR (degenerate)."""
        r = np.full(100, -0.01)
        var = var_historical_daily(r)
        cvar = cvar_historical_daily(r)
        np.testing.assert_allclose(var, cvar, atol=1e-12)


# ---------------------------------------------------------------------------
# 4. build_risk_metrics_bundle
# ---------------------------------------------------------------------------

class TestBuildRiskMetricsBundle:
    def test_parametric_only(self):
        """When no daily panel is provided, only parametric keys present."""
        m = build_risk_metrics_bundle(
            portfolio_volatility=0.20, weights=np.array([0.5, 0.5]),
            has_empirical_cov=False,
        )
        assert "var_95_parametric" in m
        assert "cvar_95_parametric" in m
        assert "var_95" in m and m["var_95"] == m["var_95_parametric"]
        assert "cvar" in m and m["cvar"] == m["cvar_95_parametric"]
        assert "var_95_historical" not in m
        assert m["correlation_source"] == "matrix_no_panel"

    def test_with_daily_panel(self, synthetic_daily):
        daily, _, weights = synthetic_daily
        m = build_risk_metrics_bundle(
            portfolio_volatility=0.20, weights=weights,
            daily_returns=daily, has_empirical_cov=True,
        )
        assert "var_95_historical" in m
        assert "cvar_95" in m
        assert m["correlation_source"] == "empirical"

    def test_short_panel_skipped(self):
        """Fewer than 30 observations → historical metrics omitted."""
        daily = np.random.default_rng(0).normal(0, 0.01, size=(10, 3))
        m = build_risk_metrics_bundle(
            portfolio_volatility=0.15,
            weights=np.array([0.4, 0.3, 0.3]),
            daily_returns=daily,
        )
        assert "var_95_historical" not in m

    def test_backward_compat_aliases(self, synthetic_daily):
        """var_95 and cvar must always be present (dashboard reads them)."""
        daily, _, weights = synthetic_daily
        m = build_risk_metrics_bundle(
            portfolio_volatility=0.18, weights=weights, daily_returns=daily,
        )
        assert "var_95" in m
        assert "cvar" in m


# ---------------------------------------------------------------------------
# 5. Integration: optimize endpoint returns new risk_metrics shape
# ---------------------------------------------------------------------------

class TestOptimizeRiskMetricsIntegration:
    """Hit the real optimize endpoint with a mock market payload that includes
    a daily return panel; assert the response includes the new keys."""

    @pytest.fixture
    def client(self):
        os.environ.pop("API_KEY", None)
        from api import app
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = False
        with app.test_client() as c:
            yield c

    def test_risk_metrics_keys_present(self, client):
        rng = np.random.default_rng(99)
        n, T = 4, 120
        daily = rng.normal(0, 0.01, size=(T, n))
        cov = np.cov(daily, rowvar=False) * 252
        returns = daily.mean(axis=0) * 252

        payload = {
            "returns": returns.tolist(),
            "covariance": cov.tolist(),
            "daily_returns": daily.tolist(),
            "objective": "markowitz",
        }
        resp = client.post("/api/portfolio/optimize", json=payload)
        assert resp.status_code == 200, resp.get_json()

        data = resp.get_json()
        rm = data.get("data", data).get("risk_metrics", {})

        assert "var_95" in rm, "backward-compat key missing"
        assert "cvar" in rm, "backward-compat key missing"
        assert "var_95_parametric" in rm
        assert "cvar_95_parametric" in rm
        assert "var_95_historical" in rm, "historical VaR should be present with daily panel"
        assert "cvar_95" in rm, "historical CVaR should be present with daily panel"
        assert rm["correlation_source"] == "empirical"
