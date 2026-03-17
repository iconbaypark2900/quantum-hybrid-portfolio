#!/usr/bin/env python3
"""
Basic example of using the portfolio optimization API.

Uses the unified run_optimization service with notebook-based methods
(hybrid, QUBO-SA, VQE) and classical optimizers.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from services.portfolio_optimizer import run_optimization


def download_sample_data():
    """Download sample S&P 500 data for testing."""
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-B', 'JNJ',
               'JPM', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'NVDA', 'PYPL', 'BAC',
               'VZ', 'ADBE', 'NFLX', 'KO', 'NKE', 'PFE', 'PEP', 'T', 'MRK', 'WMT',
               'ABT', 'CVX']

    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)

    print(f"Downloading data for {len(symbols)} stocks...")
    raw_data = yf.download(symbols, start=start_date, end=end_date, progress=False, auto_adjust=True)

    if isinstance(raw_data.columns, pd.MultiIndex):
        if 'Close' in raw_data.columns.get_level_values(0):
            data = raw_data['Close']
        else:
            data = raw_data[raw_data.columns.get_level_values(0)[0]]
    else:
        data = raw_data

    data = data.ffill().bfill()
    data = data.dropna(axis=1, how='all')

    print(f"Successfully downloaded {len(data.columns)} stocks with {len(data)} days of data")
    return data


def run_basic_optimization():
    """Run basic portfolio optimization example."""
    print("="*60)
    print("PORTFOLIO OPTIMIZATION")
    print("="*60)

    market_data = download_sample_data()
    print(f"Downloaded data for {len(market_data.columns)} stocks")
    print(f"Date range: {market_data.index[0]} to {market_data.index[-1]}")

    returns = market_data.pct_change().mean() * 252
    covariance = market_data.pct_change().cov() * 252

    print("\nRunning hybrid pipeline optimization...")
    result = run_optimization(
        returns=returns.values,
        covariance=covariance.values,
        objective='hybrid',
    )

    print("\n" + "-"*40)
    print("OPTIMIZATION RESULTS")
    print("-"*40)
    print(f"Expected Return: {result.expected_return*100:.2f}%")
    print(f"Volatility: {result.volatility*100:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"Number of active assets: {np.sum(result.weights > 0.001)}")

    print("\nTop 10 Holdings:")
    top_holdings = pd.DataFrame({
        'Asset': market_data.columns,
        'Weight': result.weights
    }).sort_values('Weight', ascending=False).head(10)

    for _, row in top_holdings.iterrows():
        print(f"  {row['Asset']}: {row['Weight']*100:.2f}%")

    return result


if __name__ == "__main__":
    optimization_result = run_basic_optimization()
    print("\nOptimization complete!")
    print("Run the API server: python middleware/api.py")
    print("Or explore examples: python examples/quantum_integration_example.py")
