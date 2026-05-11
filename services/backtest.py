"""
Backtesting service for portfolio strategies.

Runs periodic rebalances using optimization over historical lookback windows,
computes equity curve and summary metrics.

Price history is fetched via ``services.data_provider_v2.fetch_price_panel``
which uses the configured market data provider (Tiingo by default when
TIINGO_API_KEY is set, otherwise yfinance as fallback).
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd

from services.data_provider_v2 import fetch_price_panel
from services.market_data import get_asset_metadata
from services.portfolio_optimizer import run_optimization
from services.constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


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


# ─── Walk-Forward Backtest ───────────────────────────────────────────────────

def _generate_wf_periods(
    start_dt: datetime,
    end_dt: datetime,
    train_months: int,
    test_months: int,
) -> List[Tuple[datetime, datetime, datetime, datetime]]:
    """Generate (train_start, train_end, test_start, test_end) tuples.

    Each period advances by *test_months* so the test windows are
    non-overlapping and contiguous.
    """
    from dateutil.relativedelta import relativedelta

    periods: List[Tuple[datetime, datetime, datetime, datetime]] = []
    cursor = start_dt
    while True:
        train_start = cursor
        train_end = cursor + relativedelta(months=train_months)
        test_start = train_end
        test_end = test_start + relativedelta(months=test_months)
        if test_start >= end_dt:
            break
        if test_end > end_dt:
            test_end = end_dt
        periods.append((train_start, train_end, test_start, test_end))
        cursor += relativedelta(months=test_months)
    return periods


def _max_drawdown_from_values(values: List[float]) -> float:
    peak = values[0] if values else 1.0
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def walk_forward_backtest(
    tickers: List[str],
    start: str,
    end: str,
    train_months: int = 12,
    test_months: int = 3,
    objective: str = "hybrid",
    constraints: Optional[PortfolioConstraints] = None,
    cost_bps: float = 0.0,
    benchmark_ticker: Optional[str] = None,
    regime_switching: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Walk-forward backtest: train on [t, t+train], test on [t+train, t+train+test].

    Returns the roadmap contract: equity_curve, summary, periods, metadata.
    """
    if not tickers:
        raise ValueError("Tickers cannot be empty")
    if len(tickers) < 2:
        raise ValueError("Need at least 2 assets for walk-forward backtest")

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    if start_dt >= end_dt:
        raise ValueError("Start date must be before end date")
    if train_months < 6:
        raise ValueError("train_months must be >= 6")
    if test_months < 1:
        raise ValueError("test_months must be >= 1")

    periods = _generate_wf_periods(start_dt, end_dt, train_months, test_months)
    if not periods:
        raise ValueError("Date range too short for the requested train/test split")

    constraints = constraints or PortfolioConstraints()

    all_tickers = list(tickers)
    if benchmark_ticker and benchmark_ticker not in all_tickers:
        all_tickers.append(benchmark_ticker)

    full_prices = fetch_price_panel(all_tickers, start, end)
    if full_prices.empty or len(full_prices.columns) < 2:
        raise ValueError("Insufficient price data for walk-forward backtest")

    asset_tickers = [t for t in tickers if t in full_prices.columns]
    if len(asset_tickers) < 2:
        raise ValueError("Fewer than 2 tickers found in price data")

    has_benchmark = benchmark_ticker is not None and benchmark_ticker in full_prices.columns

    n = len(asset_tickers)
    prev_weights = np.ones(n) / n

    eq_dates: List[str] = []
    eq_portfolio: List[float] = []
    eq_benchmark: List[float] = []
    period_records: List[Dict[str, Any]] = []
    turnover_series: List[float] = []

    cum_equity = 1.0
    cum_bench = 1.0
    total_cost_bps_accum = 0.0

    for train_start, train_end, test_start, test_end in periods:
        ts = train_start.strftime("%Y-%m-%d")
        te = train_end.strftime("%Y-%m-%d")
        xs = test_start.strftime("%Y-%m-%d")
        xe = test_end.strftime("%Y-%m-%d")

        train_prices = full_prices.loc[ts:te, asset_tickers]
        if len(train_prices) < 20:
            logger.warning("wf_backtest: skipping period %s-%s, insufficient train data (%d rows)", ts, te, len(train_prices))
            continue

        rets = train_prices.pct_change().dropna()
        if len(rets) < 10:
            continue

        ann_returns = rets.mean().values * 252
        ann_cov = rets.cov().values * 252
        ann_cov = ann_cov + 1e-6 * np.eye(len(ann_cov))

        if regime_switching:
            try:
                from services.regime_detector import classify_regime_threshold, REGIME_OBJECTIVES
                ew_series = rets.mean(axis=1)
                reg = classify_regime_threshold(ew_series)
                used_objective = REGIME_OBJECTIVES.get(reg, objective)
            except Exception:
                reg = "unknown"
                used_objective = objective
        else:
            reg = None
            used_objective = objective

        opt = run_optimization(
            ann_returns, ann_cov,
            objective=used_objective,
            constraints=constraints,
            asset_names=asset_tickers,
        )
        new_weights = opt.weights

        turnover = float(np.sum(np.abs(new_weights - prev_weights)) / 2)
        cost = turnover * cost_bps / 10_000
        cum_equity *= (1 - cost)
        total_cost_bps_accum += turnover * cost_bps

        test_prices = full_prices.loc[xs:xe, asset_tickers]
        if len(test_prices) < 2:
            period_records.append({
                "train_start": ts, "train_end": te,
                "test_start": xs, "test_end": xe,
                "turnover": turnover,
                "weights": {t: float(w) for t, w in zip(asset_tickers, new_weights)},
                "period_return": 0.0,
                "regime": reg,
                "objective_used": used_objective,
            })
            turnover_series.append(turnover)
            prev_weights = new_weights
            continue

        daily_rets = test_prices.pct_change().dropna()
        port_daily = daily_rets.values @ new_weights

        for i, (dt_idx, dr) in enumerate(zip(daily_rets.index, port_daily)):
            cum_equity *= (1 + dr)
            d_str = dt_idx.strftime("%Y-%m-%d") if hasattr(dt_idx, "strftime") else str(dt_idx)[:10]
            eq_dates.append(d_str)
            eq_portfolio.append(float(cum_equity))

            if has_benchmark:
                bench_col = full_prices[benchmark_ticker]
                try:
                    b_today = bench_col.loc[dt_idx]
                    b_prev_idx = daily_rets.index[i - 1] if i > 0 else test_prices.index[0]
                    b_prev = bench_col.loc[b_prev_idx]
                    if i == 0:
                        cum_bench *= 1.0
                    else:
                        cum_bench *= (1 + (b_today - b_prev) / b_prev) if b_prev > 0 else 1.0
                except (KeyError, IndexError):
                    pass
                eq_benchmark.append(float(cum_bench))

        period_ret = float(
            test_prices.iloc[-1].values @ new_weights / (test_prices.iloc[0].values @ new_weights) - 1
        ) if len(test_prices) >= 2 else 0.0

        period_records.append({
            "train_start": ts, "train_end": te,
            "test_start": xs, "test_end": xe,
            "turnover": turnover,
            "weights": {t: float(w) for t, w in zip(asset_tickers, new_weights)},
            "period_return": float(period_ret),
            "regime": reg,
            "objective_used": used_objective,
        })
        turnover_series.append(turnover)
        prev_weights = new_weights

    if not eq_portfolio:
        raise ValueError("No valid test periods produced equity data")

    daily_returns = np.diff([1.0] + eq_portfolio) / ([1.0] + eq_portfolio[:-1])
    ann_ret = float(np.mean(daily_returns) * 252) if len(daily_returns) > 0 else 0.0
    ann_vol = float(np.std(daily_returns) * np.sqrt(252)) if len(daily_returns) > 0 else 0.0
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    max_dd = _max_drawdown_from_values([1.0] + eq_portfolio)

    avg_turnover = float(np.mean(turnover_series)) if turnover_series else 0.0

    data_source = os.getenv("DATA_PROVIDER", "tiingo" if os.getenv("TIINGO_API_KEY") else "yfinance")

    equity_curve: Dict[str, Any] = {
        "dates": eq_dates,
        "portfolio": eq_portfolio,
    }
    if has_benchmark and eq_benchmark:
        equity_curve["benchmark"] = eq_benchmark

    return {
        "equity_curve": equity_curve,
        "summary": {
            "annualized_return": ann_ret,
            "annualized_volatility": ann_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": -abs(max_dd),
            "avg_turnover": avg_turnover,
            "total_cost_bps": float(total_cost_bps_accum),
        },
        "periods": period_records,
        "metadata": {
            "n_periods": len(period_records),
            "objective": objective,
            "cost_bps": cost_bps,
            "data_source": data_source,
            "regime_switching": regime_switching,
        },
    }
