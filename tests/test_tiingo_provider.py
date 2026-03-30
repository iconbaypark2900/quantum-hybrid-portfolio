"""
Unit tests for TiingoProvider and its integration with MarketDataProvider.

All network calls are mocked; no real TIINGO_API_KEY is required.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_tiingo_price_response(ticker: str, n_days: int = 60):
    """Build a fake Tiingo daily price response (list of dicts)."""
    dates = pd.date_range(end=datetime.today(), periods=n_days, freq="B")
    base = 100.0
    np.random.seed(42)
    closes = list(base * np.cumprod(1 + np.random.randn(n_days) * 0.01 + 0.0003))
    return [
        {
            "date": d.strftime("%Y-%m-%dT00:00:00+00:00"),
            "close": c,
            "adjClose": c,
            "open": c,
            "high": c * 1.01,
            "low": c * 0.99,
            "volume": 1000000,
        }
        for d, c in zip(dates, closes)
    ]


def _make_tiingo_meta_response(ticker: str):
    return {
        "ticker": ticker,
        "name": f"{ticker} Inc.",
        "description": f"Description for {ticker}",
        "exchangeCode": "NASDAQ",
        "startDate": "2010-01-04",
        "endDate": datetime.today().strftime("%Y-%m-%d"),
    }


# ── TiingoProvider tests ──────────────────────────────────────────────────────

class TestTiingoProvider:
    """Tests for TiingoProvider with mocked HTTP."""

    def _make_provider(self, api_key="test-api-key"):
        with patch.dict(os.environ, {"TIINGO_API_KEY": api_key}):
            from services.data_provider_v2 import TiingoProvider
            return TiingoProvider()

    def test_available_when_api_key_set(self):
        provider = self._make_provider("my-key")
        assert provider.is_available() is True

    def test_not_available_when_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TIINGO_API_KEY", None)
            from services.data_provider_v2 import TiingoProvider
            p = TiingoProvider()
        assert p.is_available() is False

    def test_get_name(self):
        provider = self._make_provider()
        assert provider.get_name() == "tiingo"

    @patch("services.data_provider_v2.TiingoProvider._get")
    def test_fetch_prices_returns_correct_shape(self, mock_get):
        tickers = ["AAPL", "MSFT"]
        mock_get.side_effect = [
            _make_tiingo_price_response("AAPL"),
            _make_tiingo_price_response("MSFT"),
        ]
        provider = self._make_provider()
        prices = provider.fetch_prices(tickers, "2023-01-01", "2023-12-31")

        assert isinstance(prices, pd.DataFrame)
        assert set(prices.columns) == {"AAPL", "MSFT"}
        assert len(prices) > 0
        assert prices.dtypes["AAPL"] == float

    @patch("services.data_provider_v2.TiingoProvider._get")
    def test_fetch_prices_drops_failed_tickers(self, mock_get):
        """If one ticker fails, others are still returned."""
        mock_get.side_effect = [
            Exception("network error"),     # AAPL fails
            _make_tiingo_price_response("MSFT"),  # MSFT ok
        ]
        provider = self._make_provider()
        prices = provider.fetch_prices(["AAPL", "MSFT"], "2023-01-01", "2023-12-31")

        assert "MSFT" in prices.columns
        assert "AAPL" not in prices.columns

    @patch("services.data_provider_v2.TiingoProvider._get")
    def test_fetch_prices_raises_if_all_tickers_fail(self, mock_get):
        mock_get.side_effect = Exception("network error")
        provider = self._make_provider()
        with pytest.raises(ValueError, match="no price data"):
            provider.fetch_prices(["AAPL", "MSFT"], "2023-01-01", "2023-12-31")

    @patch("services.data_provider_v2.TiingoProvider._get")
    def test_fetch_ticker_meta_returns_name(self, mock_get):
        mock_get.return_value = _make_tiingo_meta_response("AAPL")
        provider = self._make_provider()
        meta = provider.fetch_ticker_meta("AAPL")
        assert meta["name"] == "AAPL Inc."
        assert meta["sector"] == "Unknown"  # Tiingo daily doesn't expose sector

    @patch("services.data_provider_v2.TiingoProvider._get")
    def test_fetch_ticker_meta_falls_back_on_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        provider = self._make_provider()
        meta = provider.fetch_ticker_meta("AAPL")
        assert meta["name"] == "AAPL"
        assert meta["sector"] == "Unknown"


# ── MarketDataProvider integration tests ────────────────────────────────────

class TestMarketDataProviderWithTiingo:
    """Tests for MarketDataProvider configured with Tiingo."""

    def test_fetch_market_data_uses_tiingo(self, monkeypatch):
        """MarketDataProvider routes to Tiingo when TIINGO_API_KEY is set."""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        monkeypatch.setenv("TIINGO_API_KEY", "test-key")
        monkeypatch.setenv("DATA_PROVIDER", "tiingo")

        from services.data_provider_v2 import MarketDataProvider
        provider = MarketDataProvider(provider="tiingo")
        assert provider.primary_provider == "tiingo"

        synthetic_prices = pd.DataFrame(
            {t: 100 * np.cumprod(1 + np.random.randn(100) * 0.01) for t in tickers},
            index=pd.date_range("2023-01-01", periods=100, freq="B"),
        )
        meta = {t: {"name": f"{t} Inc.", "sector": "Unknown"} for t in tickers}

        with patch.object(provider._providers["tiingo"], "fetch_prices",
                          return_value=synthetic_prices):
            with patch.object(provider, "_resolve_metadata", return_value=meta):
                result = provider.fetch_market_data(
                    tickers,
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                )

        assert result["provider"] == "tiingo"
        assert set(result["assets"]) <= set(tickers)
        assert len(result["returns"]) == len(result["assets"])
        assert result["success"] is True

    def test_fetch_price_panel_returns_dataframe(self, monkeypatch):
        """fetch_price_panel returns a raw date × ticker DataFrame."""
        tickers = ["AAPL", "MSFT"]
        monkeypatch.setenv("TIINGO_API_KEY", "test-key")
        monkeypatch.setenv("DATA_PROVIDER", "tiingo")

        from services.data_provider_v2 import MarketDataProvider
        provider = MarketDataProvider(provider="tiingo")

        synthetic_prices = pd.DataFrame(
            {t: 100 * np.cumprod(1 + np.random.randn(100) * 0.01) for t in tickers},
            index=pd.date_range("2023-01-01", periods=100, freq="B"),
        )

        with patch.object(provider._providers["tiingo"], "fetch_prices",
                          return_value=synthetic_prices):
            prices = provider.fetch_price_panel(tickers, "2023-01-01", "2023-12-31")

        assert isinstance(prices, pd.DataFrame)
        assert set(prices.columns) == set(tickers)
        assert len(prices) > 0

    def test_output_shape_matches_expected_contract(self, monkeypatch):
        """fetch_market_data result always contains the required keys."""
        required_keys = {"assets", "names", "sectors", "returns", "covariance",
                         "start_date", "end_date", "data_points", "provider", "success"}

        tickers = ["AAPL", "MSFT"]
        monkeypatch.setenv("TIINGO_API_KEY", "test-key")
        monkeypatch.setenv("DATA_PROVIDER", "tiingo")

        # Use a simple synthetic price panel and bypass the real HTTP call
        import importlib
        import services.data_provider_v2 as dpv2
        importlib.reload(dpv2)

        synthetic_prices = pd.DataFrame(
            {
                "AAPL": 100 * np.cumprod(1 + np.random.randn(100) * 0.01),
                "MSFT": 100 * np.cumprod(1 + np.random.randn(100) * 0.01),
            },
            index=pd.date_range("2023-01-01", periods=100, freq="B"),
        )

        provider = dpv2.MarketDataProvider(provider="tiingo")

        # Patch at the provider level so no network is hit
        with patch.object(provider._providers["tiingo"], "fetch_prices", return_value=synthetic_prices):
            with patch.object(provider, "_resolve_metadata",
                              return_value={t: {"name": t, "sector": "Unknown"} for t in tickers}):
                result = provider.fetch_market_data(tickers, "2023-01-01", "2023-12-31")

        assert required_keys.issubset(result.keys())
        assert len(result["returns"]) == len(result["assets"])
        assert len(result["covariance"]) == len(result["assets"])

    def test_resolve_metadata_merges_yfinance_sector_when_configured(self, monkeypatch):
        """METADATA_SECTOR_SOURCE=yfinance overlays sector/industry on Tiingo meta."""
        monkeypatch.setenv("TIINGO_API_KEY", "test-key")
        monkeypatch.setenv("DATA_PROVIDER", "tiingo")
        monkeypatch.setenv("METADATA_SECTOR_SOURCE", "yfinance")

        from services.data_provider_v2 import MarketDataProvider

        provider = MarketDataProvider(provider="tiingo")
        tickers = ["AAPL", "MSFT"]

        fake_tiingo_meta = {
            "AAPL": {
                "name": "Apple Inc.",
                "sector": "Unknown",
                "industry": "Unknown",
                "market_cap": None,
                "currency": "USD",
                "exchange": "NASDAQ",
            },
            "MSFT": {
                "name": "Microsoft Corporation",
                "sector": "Unknown",
                "industry": "Unknown",
                "market_cap": None,
                "currency": "USD",
                "exchange": "NASDAQ",
            },
        }
        fake_yf_sectors = {
            "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
            "MSFT": {"sector": "Technology", "industry": "Software—Infrastructure"},
        }

        with patch.object(provider._providers["tiingo"], "fetch_ticker_meta") as mock_tm:
            mock_tm.side_effect = lambda t: fake_tiingo_meta[t].copy()
            with patch(
                "services.market_data.get_yfinance_sector_industry",
                return_value=fake_yf_sectors,
            ):
                out = provider._resolve_metadata(tickers, "tiingo")

        assert out["AAPL"]["name"] == "Apple Inc."
        assert out["AAPL"]["sector"] == "Technology"
        assert out["AAPL"]["industry"] == "Consumer Electronics"
        assert out["MSFT"]["sector"] == "Technology"

    def test_resolve_metadata_skips_yfinance_merge_when_not_configured(self, monkeypatch):
        monkeypatch.setenv("TIINGO_API_KEY", "test-key")
        monkeypatch.setenv("DATA_PROVIDER", "tiingo")
        monkeypatch.delenv("METADATA_SECTOR_SOURCE", raising=False)

        from services.data_provider_v2 import MarketDataProvider

        provider = MarketDataProvider(provider="tiingo")
        tickers = ["AAPL"]

        with patch.object(provider._providers["tiingo"], "fetch_ticker_meta",
                          return_value={"name": "Apple Inc.", "sector": "Unknown", "industry": "Unknown",
                                        "market_cap": None, "currency": "USD", "exchange": "NASDAQ"}):
            with patch("services.market_data.get_yfinance_sector_industry") as mock_yf:
                out = provider._resolve_metadata(tickers, "tiingo")

        mock_yf.assert_not_called()
        assert out["AAPL"]["sector"] == "Unknown"
