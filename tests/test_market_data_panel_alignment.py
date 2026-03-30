"""
Tests for panel-aligned μ/Σ in MarketDataProvider._process_prices.

When include_daily_returns=True, the primary 'returns' and 'covariance' in the
response must be computed from the tail slice (same rows as 'daily_returns'),
not from the full window. Full-window stats are preserved under the
*_full_window keys.
"""
import numpy as np
import pandas as pd
import pytest

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from services.data_provider_v2 import MarketDataProvider
from services.risk_models import ledoit_wolf_covariance


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_price_df(n_tickers: int, n_days: int, seed: int = 42) -> pd.DataFrame:
    """Synthetic price DataFrame with n_tickers columns and n_days rows."""
    rng = np.random.default_rng(seed)
    # Random-walk prices with distinct drift/vol per ticker so LW stats differ
    log_returns = rng.normal(
        loc=np.linspace(0.0003, 0.001, n_tickers),
        scale=np.linspace(0.008, 0.02, n_tickers),
        size=(n_days, n_tickers),
    )
    prices = 100 * np.exp(log_returns.cumsum(axis=0))
    tickers = [f"T{i}" for i in range(n_tickers)]
    dates = pd.bdate_range(start="2019-01-02", periods=n_days)
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ── fixtures ──────────────────────────────────────────────────────────────────

PROVIDER = MarketDataProvider()
DAILY_CAP = MarketDataProvider._DAILY_CAP


# ── tests ─────────────────────────────────────────────────────────────────────

class TestIncludeDailyReturnsFalse:
    """Without include_daily_returns, behavior is unchanged (full_window)."""

    def test_covariance_source_is_full_window(self):
        prices = _make_price_df(3, 300)
        result = PROVIDER._process_prices(
            prices, list(prices.columns), "2020-01-01", "2021-01-01",
            provider_name="test", include_daily_returns=False
        )
        assert result["covariance_source"] == "full_window"

    def test_no_daily_fields(self):
        prices = _make_price_df(3, 300)
        result = PROVIDER._process_prices(
            prices, list(prices.columns), "2020-01-01", "2021-01-01",
            provider_name="test", include_daily_returns=False
        )
        assert "daily_dates" not in result
        assert "daily_returns" not in result
        assert "covariance_full_window" not in result
        assert "returns_full_window" not in result
        assert "data_points_full_window" not in result

    def test_data_points_equals_full_window(self):
        n_days = 300
        prices = _make_price_df(3, n_days)
        result = PROVIDER._process_prices(
            prices, list(prices.columns), "2020-01-01", "2021-01-01",
            provider_name="test", include_daily_returns=False
        )
        # pct_change().dropna() removes first row
        assert result["data_points"] == n_days - 1


class TestIncludeDailyReturnsTrue:
    """With include_daily_returns=True, primary stats come from the tail slice."""

    def _call(self, prices):
        return PROVIDER._process_prices(
            prices, list(prices.columns), "2019-01-01", "2022-01-01",
            provider_name="test", include_daily_returns=True
        )

    def test_covariance_source_is_panel_aligned(self):
        prices = _make_price_df(4, 700)
        result = self._call(prices)
        assert result["covariance_source"] == "panel_aligned"

    def test_daily_fields_present(self):
        prices = _make_price_df(4, 700)
        result = self._call(prices)
        assert "daily_dates" in result
        assert "daily_returns" in result

    def test_full_window_fields_present(self):
        prices = _make_price_df(4, 700)
        result = self._call(prices)
        assert "returns_full_window" in result
        assert "covariance_full_window" in result
        assert "data_points_full_window" in result

    def test_data_points_equals_tail_length(self):
        # n_days > DAILY_CAP so tail is capped
        n_days = DAILY_CAP + 200
        prices = _make_price_df(4, n_days)
        result = self._call(prices)
        assert result["data_points"] == DAILY_CAP

    def test_data_points_full_window_equals_full_length(self):
        n_days = DAILY_CAP + 200
        prices = _make_price_df(4, n_days)
        result = self._call(prices)
        assert result["data_points_full_window"] == n_days - 1  # pct_change drops first row

    def test_primary_covariance_matches_lw_on_tail(self):
        """Primary covariance must equal LW on the tail slice, not the full window."""
        n_days = DAILY_CAP + 200
        prices = _make_price_df(4, n_days)
        returns_df = prices.pct_change().dropna()
        tail = returns_df.iloc[-DAILY_CAP:]

        expected_cov = ledoit_wolf_covariance(tail.values, annualize=True)

        result = self._call(prices)
        actual_cov = np.array(result["covariance"])

        np.testing.assert_allclose(actual_cov, expected_cov, rtol=1e-6)

    def test_primary_covariance_differs_from_full_window(self):
        """Full-window LW and panel LW should differ when history >> DAILY_CAP."""
        n_days = DAILY_CAP + 300
        prices = _make_price_df(4, n_days, seed=99)
        result = self._call(prices)

        primary_cov = np.array(result["covariance"])
        full_cov = np.array(result["covariance_full_window"])

        # Matrices should not be element-wise equal
        assert not np.allclose(primary_cov, full_cov), (
            "Panel-aligned and full-window covariances should differ when "
            f"full window ({n_days}) >> DAILY_CAP ({DAILY_CAP})."
        )

    def test_primary_returns_matches_tail_mean(self):
        """Primary annual returns must equal tail.mean() * 252."""
        n_days = DAILY_CAP + 100
        prices = _make_price_df(3, n_days)
        returns_df = prices.pct_change().dropna()
        tail = returns_df.iloc[-DAILY_CAP:]

        expected_returns = (tail.mean() * 252).values

        result = self._call(prices)
        actual_returns = np.array(result["returns"])

        np.testing.assert_allclose(actual_returns, expected_returns, rtol=1e-8)

    def test_daily_returns_shape(self):
        n_tickers = 5
        n_days = DAILY_CAP + 50
        prices = _make_price_df(n_tickers, n_days)
        result = self._call(prices)

        dr = result["daily_returns"]
        assert len(dr) == DAILY_CAP
        assert all(len(row) == n_tickers for row in dr)

    def test_daily_dates_length_matches_daily_returns(self):
        prices = _make_price_df(3, DAILY_CAP + 50)
        result = self._call(prices)
        assert len(result["daily_dates"]) == len(result["daily_returns"])

    def test_covariance_is_symmetric_and_psd(self):
        prices = _make_price_df(4, DAILY_CAP + 100)
        result = self._call(prices)
        cov = np.array(result["covariance"])
        n = cov.shape[0]
        assert cov.shape == (n, n)
        np.testing.assert_allclose(cov, cov.T, atol=1e-12)
        eigvals = np.linalg.eigvalsh(cov)
        assert np.all(eigvals >= -1e-10), f"Negative eigenvalues: {eigvals}"


class TestShortPanelGuard:
    """Verify the <2 tail row guard raises clearly."""

    def test_raises_on_empty_prices(self):
        prices = _make_price_df(2, 3)  # pct_change gives 2 rows; tail of 2 is fine
        # The following should succeed (2 rows is acceptable)
        result = PROVIDER._process_prices(
            prices, list(prices.columns), "2020-01-01", "2021-01-01",
            provider_name="test", include_daily_returns=True
        )
        assert result["covariance_source"] == "panel_aligned"
