"""
Backtesting service for portfolio strategies.

Runs periodic rebalances using optimization over historical lookback windows,
computes equity curve and summary metrics.

Price history is fetched via ``services.data_provider_v2.fetch_price_panel``
which uses the configured market data provider (Tiingo by default when
TIINGO_API_KEY is set, otherwise yfinance as fallback).
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from services.data_provider_v2 import fetch_price_panel
from services.market_data import get_asset_metadata
from services.portfolio_optimizer import run_optimization
from services.constraints import PortfolioConstraints


def _get_rebalance_dates(
    start: datetime,
    end: datetime,
    frequency: str,
) -> List[datetime]:
    """Get rebalance dates in range [start, end] for given frequency."""
    from dateutil.relativedelta import relativedelta

    dates = []
    current = start

    while current <= end:
        dates.append(current)
        if frequency == "weekly":
            current += relativedelta(weeks=1)
        elif frequency == "monthly":
            current += relativedelta(months=1)
        elif frequency == "quarterly":
            current += relativedelta(months=3)
        elif frequency == "yearly":
            current += relativedelta(years=1)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

    return dates


def run_backtest(
    tickers: List[str],
    start_date: str,
    end_date: str,
    rebalance_frequency: str = "monthly",
    objective: str = "max_sharpe",
    target_return: Optional[float] = None,
    strategy_preset: str = "balanced",
    constraints: Optional[PortfolioConstraints] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Run backtest: rebalance at each date, optimize over lookback, compute equity curve.

    Returns:
        Dict with results, summary_metrics, parameters.
    """
    if not tickers:
        raise ValueError("Tickers cannot be empty")
    if len(tickers) < 2:
        raise ValueError("Need at least 2 assets for backtest")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    if start_dt >= end_dt:
        raise ValueError("Start date must be before end date")

    valid_freqs = ["weekly", "monthly", "quarterly", "yearly"]
    if rebalance_frequency not in valid_freqs:
        raise ValueError(f"Invalid rebalance frequency. Valid options: {valid_freqs}")

    # Fetch full price history via unified provider (Tiingo, or fallback)
    prices = fetch_price_panel(tickers, start_date, end_date)

    if prices.empty or len(prices.columns) < 2:
        raise ValueError("Insufficient price data for backtest")

    tickers = list(prices.columns)
    constraints = constraints or PortfolioConstraints()

    # Rebalance dates
    reb_dates = _get_rebalance_dates(start_dt, end_dt, rebalance_frequency)
    if not reb_dates:
        raise ValueError("No rebalance dates in range")

    # Lookback for optimization (e.g. 252 trading days)
    lookback = min(252, len(prices) // 2) or 60
    results = []
    equity = 1.0
    prev_weights = None

    for i, reb_dt in enumerate(reb_dates):
        reb_str = reb_dt.strftime("%Y-%m-%d")
        idx = prices.index.get_indexer([reb_str], method="nearest")[0]
        if idx >= len(prices):
            continue
        hist_end = prices.index[idx]
        hist_start = prices.index[max(0, idx - lookback)]
        window = prices.loc[hist_start:hist_end]

        if len(window) < 20:
            if prev_weights is not None:
                results.append({
                    "date": reb_str,
                    "weights": prev_weights.tolist(),
                    "portfolio_return": 0.0,
                    "cumulative_value": equity,
                })
            continue

        rets = window.pct_change().dropna()
        if len(rets) < 10:
            if prev_weights is not None:
                results.append({
                    "date": reb_str,
                    "weights": prev_weights.tolist(),
                    "portfolio_return": 0.0,
                    "cumulative_value": equity,
                })
            continue

        returns = rets.mean().values * 252
        cov = rets.cov().values * 252
        cov = cov + 1e-6 * np.eye(len(cov))  # regularize

        opt = run_optimization(
            returns, cov,
            objective=objective,
            target_return=target_return,
            strategy_preset=strategy_preset,
            constraints=constraints,
        )
        weights = opt.weights
        prev_weights = weights

        # Portfolio return from reb_dt to next reb or end
        next_idx = i + 1
        if next_idx < len(reb_dates):
            next_str = reb_dates[next_idx].strftime("%Y-%m-%d")
        else:
            next_str = end_date
        next_nearest = prices.index.get_indexer([next_str], method="nearest")[0]
        slice_end = min(next_nearest + 1, len(prices))
        period_prices = prices.iloc[idx:slice_end]

        if len(period_prices) < 2:
            period_ret = 0.0
        else:
            start_vals = period_prices.iloc[0].values
            end_vals = period_prices.iloc[-1].values
            period_ret = float(np.dot(weights, (end_vals / start_vals - 1)))

        equity *= 1 + period_ret
        results.append({
            "date": reb_str,
            "weights": weights.tolist(),
            "portfolio_return": float(period_ret),
            "cumulative_value": float(equity),
        })

    total_return = equity - 1.0
    period_returns = [r["portfolio_return"] for r in results if "portfolio_return" in r]
    periods_per_year = {"weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}.get(rebalance_frequency, 12)
    vol = float(np.std(period_returns) * np.sqrt(periods_per_year)) if period_returns else 0.0
    sharpe = total_return / vol if vol > 0 else 0.0

    # Max drawdown
    values = [1.0] + [r["cumulative_value"] for r in results]
    peak = 1.0
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    return {
        "results": results,
        "summary_metrics": {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "volatility": vol,
            "max_drawdown": max_dd,
        },
        "parameters": {
            "tickers": tickers,
            "start_date": start_date,
            "end_date": end_date,
            "rebalance_frequency": rebalance_frequency,
            "objective": objective,
        },
    }
