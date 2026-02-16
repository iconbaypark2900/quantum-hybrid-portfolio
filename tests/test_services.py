"""
Comprehensive tests for backend services (constraints, portfolio_optimizer, backtest, market_data).

All tests use mock/synthetic data only - no real network calls.
"""
import sys
from pathlib import Path

# Ensure project root is on path for imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.constraints import PortfolioConstraints, compute_sector_masks
from services.portfolio_optimizer import (
    run_optimization,
    OptimizationResult,
    get_config_for_preset,
)
from services.backtest import run_backtest, _get_rebalance_dates
from services.market_data import validate_tickers


# --- Synthetic data fixtures ---


def make_returns_covariance(n_assets: int = 5, seed: int = 42):
    """Generate valid returns and covariance matrix (positive semi-definite)."""
    np.random.seed(seed)
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets)
    covariance = np.dot(A.T, A) / n_assets + np.eye(n_assets) * 0.01
    return returns.astype(float), covariance.astype(float)


# ============================================================================
# 1. PortfolioConstraints tests
# ============================================================================


class TestPortfolioConstraints:
    """Tests for PortfolioConstraints dataclass."""

    def test_default_construction(self):
        """Default construction yields empty constraints."""
        c = PortfolioConstraints()
        assert c.sector_limits == {}
        assert c.sector_min == {}
        assert c.max_sector_weight is None
        assert c.cardinality is None
        assert c.blacklist == []
        assert c.whitelist == []
        assert c.has_constraints() is False

    def test_construction_with_values(self):
        """Construction with explicit values."""
        c = PortfolioConstraints(
            sector_limits={"Technology": 0.30, "Finance": 0.25},
            sector_min={"Healthcare": 0.05},
            max_sector_weight=0.40,
            cardinality=10,
            blacklist=["TSLA"],
            whitelist=["AAPL", "MSFT"],
        )
        assert c.sector_limits["Technology"] == 0.30
        assert c.sector_min["Healthcare"] == 0.05
        assert c.max_sector_weight == 0.40
        assert c.cardinality == 10
        assert "TSLA" in c.blacklist
        assert "AAPL" in c.whitelist
        assert c.has_constraints() is True

    def test_sector_limits(self):
        """Sector limits are stored correctly."""
        c = PortfolioConstraints(sector_limits={"Energy": 0.20, "Tech": 0.35})
        assert c.sector_limits["Energy"] == 0.20
        assert c.sector_limits["Tech"] == 0.35

    def test_blacklist_whitelist(self):
        """Blacklist and whitelist are stored as lists."""
        c = PortfolioConstraints(blacklist=["A", "B"], whitelist=["C", "D"])
        assert set(c.blacklist) == {"A", "B"}
        assert set(c.whitelist) == {"C", "D"}

    def test_has_constraints_true_for_any_constraint(self):
        """has_constraints returns True when any constraint is set."""
        assert PortfolioConstraints(sector_limits={"X": 0.5}).has_constraints()
        assert PortfolioConstraints(max_sector_weight=0.3).has_constraints()
        assert PortfolioConstraints(cardinality=5).has_constraints()
        assert PortfolioConstraints(min_cardinality=3).has_constraints()
        assert PortfolioConstraints(max_cardinality=8).has_constraints()
        assert PortfolioConstraints(blacklist=["A"]).has_constraints()
        assert PortfolioConstraints(whitelist=["B"]).has_constraints()
        # Note: turnover_budget is not checked in has_constraints() in constraints.py

    def test_from_dict_empty(self):
        """from_dict with None or empty dict returns default constraints."""
        assert PortfolioConstraints.from_dict(None).has_constraints() is False
        assert PortfolioConstraints.from_dict({}).has_constraints() is False

    def test_from_dict_full(self):
        """from_dict builds constraints from API-style dict."""
        d = {
            "sector_limits": {"Tech": 0.30},
            "sector_min": {"Healthcare": 0.05},
            "max_sector_weight": 0.40,
            "cardinality": 8,
            "blacklist": ["tsla", " gme "],
            "whitelist": ["AAPL", "  msft  "],
            "turnover_budget": 0.15,
        }
        c = PortfolioConstraints.from_dict(d)
        assert c.sector_limits == {"Tech": 0.30}
        assert c.sector_min == {"Healthcare": 0.05}
        assert c.max_sector_weight == 0.40
        assert c.cardinality == 8
        assert "TSLA" in c.blacklist
        assert "GME" in c.blacklist
        assert "AAPL" in c.whitelist
        assert "MSFT" in c.whitelist
        assert c.turnover_budget == 0.15


class TestComputeSectorMasks:
    """Tests for compute_sector_masks helper."""

    def test_empty_sectors(self):
        """Empty sectors returns empty dict."""
        assert compute_sector_masks([]) == {}

    def test_sector_masks(self):
        """Sectors map to indices correctly."""
        sectors = ["Tech", "Finance", "Tech", "Unknown", "Finance"]
        masks = compute_sector_masks(sectors)
        assert "Tech" in masks
        assert "Finance" in masks
        assert "Unknown" in masks
        assert masks["Tech"] == [0, 2]
        assert masks["Finance"] == [1, 4]
        assert masks["Unknown"] == [3]


# ============================================================================
# 2. run_optimization tests
# ============================================================================


class TestRunOptimization:
    """Tests for portfolio_optimizer.run_optimization with mock data."""

    def test_max_sharpe_weights_sum_to_one(self):
        """Max Sharpe optimization produces weights that sum to 1.0."""
        returns, cov = make_returns_covariance(6)
        result = run_optimization(returns, cov, objective="max_sharpe")
        assert isinstance(result, OptimizationResult)
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5
        assert result.objective == "max_sharpe"

    def test_min_variance_weights_sum_to_one(self):
        """Min variance optimization produces weights that sum to 1.0."""
        returns, cov = make_returns_covariance(6)
        result = run_optimization(returns, cov, objective="min_variance")
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5
        assert result.objective == "min_variance"

    def test_risk_parity_weights_sum_to_one(self):
        """Risk parity optimization produces weights that sum to 1.0."""
        returns, cov = make_returns_covariance(6)
        result = run_optimization(returns, cov, objective="risk_parity")
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5
        assert result.objective == "risk_parity"

    def test_target_return_weights_sum_to_one(self):
        """Target return optimization produces weights that sum to 1.0."""
        returns, cov = make_returns_covariance(6)
        target = float(np.mean(returns))
        result = run_optimization(
            returns, cov, objective="target_return", target_return=target
        )
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5
        # May fall back to min_variance if target is infeasible
        assert result.objective in ("target_return", "min_variance")

    def test_result_has_expected_keys(self):
        """OptimizationResult has required attributes."""
        returns, cov = make_returns_covariance(5)
        result = run_optimization(returns, cov, objective="min_variance")
        assert hasattr(result, "weights")
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "expected_return")
        assert hasattr(result, "volatility")
        assert hasattr(result, "turnover")
        assert hasattr(result, "objective")
        assert hasattr(result, "n_active")

    def test_weights_non_negative(self):
        """Weights are non-negative (long-only)."""
        returns, cov = make_returns_covariance(6)
        for obj in ["max_sharpe", "min_variance", "risk_parity"]:
            result = run_optimization(returns, cov, objective=obj)
            assert np.all(result.weights >= -1e-9), f"objective={obj}"

    def test_constraints_sector_limits_respected(self):
        """Sector limits are respected when sectors provided."""
        n = 6
        returns, cov = make_returns_covariance(n)
        sectors = ["Tech", "Tech", "Finance", "Finance", "Energy", "Energy"]
        constraints = PortfolioConstraints(
            sector_limits={"Tech": 0.30, "Finance": 0.30, "Energy": 0.40}
        )
        result = run_optimization(
            returns, cov,
            objective="min_variance",
            constraints=constraints,
            sectors=sectors,
        )
        masks = compute_sector_masks(sectors)
        for sector, limit in constraints.sector_limits.items():
            if sector in masks:
                sector_weight = sum(result.weights[i] for i in masks[sector])
                # Use looser tolerance for floating-point
                assert sector_weight <= limit + 1e-3, f"Sector {sector} exceeded limit"

    def test_blacklist_excludes_assets(self):
        """Blacklisted assets receive zero weight."""
        n = 5
        returns, cov = make_returns_covariance(n)
        asset_names = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        constraints = PortfolioConstraints(blacklist=["TSLA", "AMZN"])
        result = run_optimization(
            returns, cov,
            objective="min_variance",
            constraints=constraints,
            asset_names=asset_names,
        )
        # After filtering, universe is AAPL, MSFT, GOOGL. Weights are expanded back.
        assert result.weights[4] == 0  # TSLA
        assert result.weights[3] == 0  # AMZN

    def test_whitelist_restricts_universe(self):
        """Whitelist restricts to only those assets."""
        n = 5
        returns, cov = make_returns_covariance(n)
        asset_names = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        constraints = PortfolioConstraints(whitelist=["AAPL", "MSFT"])
        result = run_optimization(
            returns, cov,
            objective="min_variance",
            constraints=constraints,
            asset_names=asset_names,
        )
        # Only AAPL and MSFT should have weight; others zero
        assert result.weights[2] == 0  # GOOGL
        assert result.weights[3] == 0  # AMZN
        assert result.weights[4] == 0  # TSLA
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5

    def test_cardinality_constraint(self):
        """Cardinality limits number of active positions."""
        n = 8
        returns, cov = make_returns_covariance(n)
        constraints = PortfolioConstraints(cardinality=3)
        result = run_optimization(
            returns, cov,
            objective="min_variance",
            constraints=constraints,
        )
        assert result.n_active <= 3
        assert np.abs(np.sum(result.weights) - 1.0) < 1e-5


# ============================================================================
# 3. run_backtest tests (with mocked yfinance)
# ============================================================================


def _make_mock_price_data(tickers, start_date: str, end_date: str, n_days: int = 260):
    """Create synthetic price DataFrame matching yf.download(..., group_by='ticker').

    Columns are (Ticker, Attr) - level 0 = tickers, level 1 = OHLCV attrs.
    Backtest uses xs('Adj Close', axis=1, level=1) to extract prices.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq="B")[:n_days]
    np.random.seed(123)
    data = {}
    base = 100.0
    for t in tickers:
        rets = np.random.randn(len(dates)) * 0.01 + 0.0003
        prices = base * np.cumprod(1 + rets)
        data[t] = prices
    df = pd.DataFrame(data, index=dates)
    if len(tickers) > 1:
        attrs = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        cols = [(t, attr) for t in tickers for attr in attrs]
        mi = pd.MultiIndex.from_tuples(cols, names=["Ticker", "Attributes"])
        out_data = {(t, attr): df[t].values for t in tickers for attr in attrs}
        out = pd.DataFrame(out_data, index=df.index)
        out.columns = mi
        return out
    return pd.DataFrame({"Adj Close": df[tickers[0]], "Close": df[tickers[0]]})


class TestRunBacktest:
    """Tests for backtest.run_backtest with mocked yfinance."""

    @patch("services.backtest.get_asset_metadata")
    @patch("services.backtest.yf")
    def test_backtest_results_have_expected_keys(self, mock_yf, mock_metadata):
        """Backtest returns dict with results, summary_metrics, parameters."""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        start_date = "2023-01-01"
        end_date = "2023-06-30"

        mock_prices = _make_mock_price_data(tickers, start_date, end_date)
        mock_yf.download.return_value = mock_prices

        mock_metadata.return_value = {
            t: {"sector": "Technology", "name": t} for t in tickers
        }

        result = run_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency="monthly",
            objective="max_sharpe",
        )
        assert "results" in result
        assert "summary_metrics" in result
        assert "parameters" in result
        assert "total_return" in result["summary_metrics"]
        assert "sharpe_ratio" in result["summary_metrics"]
        assert "volatility" in result["summary_metrics"]
        assert "max_drawdown" in result["summary_metrics"]
        assert result["parameters"]["tickers"] == tickers
        assert result["parameters"]["start_date"] == start_date
        assert result["parameters"]["end_date"] == end_date
        assert result["parameters"]["objective"] == "max_sharpe"

    @patch("services.backtest.get_asset_metadata")
    @patch("services.backtest.yf")
    def test_backtest_invalid_empty_tickers(self, mock_yf, mock_metadata):
        """Empty tickers raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            run_backtest(tickers=[], start_date="2023-01-01", end_date="2023-12-31")

    def test_backtest_invalid_single_ticker(self):
        """Single ticker raises ValueError (need at least 2)."""
        with pytest.raises(ValueError, match="at least 2 assets"):
            run_backtest(
                tickers=["AAPL"],
                start_date="2023-01-01",
                end_date="2023-12-31",
            )

    def test_backtest_invalid_dates(self):
        """Start date >= end date raises ValueError."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            run_backtest(
                tickers=["AAPL", "MSFT"],
                start_date="2023-12-31",
                end_date="2023-01-01",
            )


class TestGetRebalanceDates:
    """Tests for _get_rebalance_dates helper."""

    def test_rebalance_dates_monthly(self):
        """Monthly rebalance produces expected dates."""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 4, 1)
        dates = _get_rebalance_dates(start, end, "monthly")
        assert len(dates) >= 2
        assert dates[0] == start
        assert dates[-1] <= end or dates[-1] == end

    def test_rebalance_dates_unsupported_frequency(self):
        """Unsupported frequency raises ValueError."""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 6, 1)
        with pytest.raises(ValueError, match="Unsupported frequency"):
            _get_rebalance_dates(start, end, "daily")


# ============================================================================
# 4. market_data validate_tickers tests
# ============================================================================


class TestValidateTickers:
    """Tests for market_data.validate_tickers."""

    def test_valid_tickers(self):
        """Valid tickers are cleaned and returned."""
        result = validate_tickers(["AAPL", "MSFT", "GOOGL"])
        assert result == ["AAPL", "MSFT", "GOOGL"]

    def test_tickers_normalized_uppercase(self):
        """Tickers are normalized to uppercase."""
        result = validate_tickers(["aapl", "MsFt"])
        assert result == ["AAPL", "MSFT"]

    def test_tickers_stripped(self):
        """Whitespace is stripped."""
        result = validate_tickers(["  AAPL  ", " MSFT "])
        assert result == ["AAPL", "MSFT"]

    def test_empty_strings_filtered(self):
        """Empty strings are filtered out."""
        result = validate_tickers(["AAPL", "", "   ", "MSFT"])
        assert result == ["AAPL", "MSFT"]

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = validate_tickers([])
        assert result == []

    def test_too_long_tickers_filtered(self):
        """Tickers longer than 10 chars are filtered out."""
        result = validate_tickers(["AAPL", "VERYLONGTICKER123", "MSFT"])
        assert result == ["AAPL", "MSFT"]

    def test_exactly_10_chars_allowed(self):
        """Tickers of length 10 are allowed."""
        ticker = "ABCDEFGHIJ"
        result = validate_tickers([ticker])
        assert result == [ticker]

    def test_non_string_items(self):
        """Non-string items may cause issues; validate handles iterable."""
        # validate_tickers iterates and calls .strip().upper() - integers would fail
        # So we test with valid strings
        result = validate_tickers(["1", "A"])  # "1" and "A" are valid
        assert "1" in result
        assert "A" in result
