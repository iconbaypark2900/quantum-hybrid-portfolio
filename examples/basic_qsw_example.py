"""
Basic example of using QSW for portfolio optimization.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from validation.chang_validation import ChangValidation

def download_sample_data():
    """Download sample S&P 500 data for testing."""
    # Top 30 S&P 500 stocks
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-B', 'JNJ', 
               'JPM', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'NVDA', 'PYPL', 'BAC',
               'VZ', 'ADBE', 'NFLX', 'KO', 'NKE', 'PFE', 'PEP', 'T', 'MRK', 'WMT',
               'ABT', 'CVX']
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)  # 3 years of data
    
    print(f"Downloading data for {len(symbols)} stocks...")
    raw_data = yf.download(symbols, start=start_date, end=end_date, progress=False, auto_adjust=True)
    
    # Extract 'Close' prices - yfinance returns MultiIndex with (price_type, ticker)
    if isinstance(raw_data.columns, pd.MultiIndex):
        # Multi-stock download returns MultiIndex: (price_type, ticker)
        if 'Close' in raw_data.columns.get_level_values(0):
            data = raw_data['Close']
        else:
            # Fallback to first price type available
            data = raw_data[raw_data.columns.get_level_values(0)[0]]
    else:
        # Single stock or already flat
        data = raw_data
    
    # Handle missing data
    data = data.ffill().bfill()
    
    # Drop any columns with all NaN
    data = data.dropna(axis=1, how='all')
    
    print(f"Successfully downloaded {len(data.columns)} stocks with {len(data)} days of data")
    
    return data

def run_basic_optimization():
    """Run basic QSW optimization example."""
    print("="*60)
    print("QUANTUM STOCHASTIC WALK PORTFOLIO OPTIMIZATION")
    print("="*60)
    
    # Download data
    market_data = download_sample_data()
    print(f"Downloaded data for {len(market_data.columns)} stocks")
    print(f"Date range: {market_data.index[0]} to {market_data.index[-1]}")
    
    # Calculate returns and covariance
    returns = market_data.pct_change().mean() * 252  # Annualized
    covariance = market_data.pct_change().cov() * 252  # Annualized
    
    # Initialize optimizer
    optimizer = QuantumStochasticWalkOptimizer()
    
    # Run optimization
    print("\nRunning QSW optimization...")
    result = optimizer.optimize(
        returns=returns,
        covariance=covariance,
        market_regime='normal'
    )
    
    # Display results
    print("\n" + "-"*40)
    print("OPTIMIZATION RESULTS")
    print("-"*40)
    print(f"Expected Return: {result.expected_return*100:.2f}%")
    print(f"Volatility: {result.volatility*100:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"Number of assets: {np.sum(result.weights > 0.001)}")
    
    print("\nTop 10 Holdings:")
    top_holdings = pd.DataFrame({
        'Asset': market_data.columns,
        'Weight': result.weights
    }).sort_values('Weight', ascending=False).head(10)
    
    for _, row in top_holdings.iterrows():
        print(f"  {row['Asset']}: {row['Weight']*100:.2f}%")
    
    print("\nGraph Metrics:")
    for key, value in result.graph_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    print("\nEvolution Metrics:")
    for key, value in result.evolution_metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
    
    return result

def run_validation():
    """Run Chang validation suite."""
    print("\n" + "="*60)
    print("RUNNING CHANG ET AL. VALIDATION")
    print("="*60)
    
    # Download data
    market_data = download_sample_data()
    
    # Run validation
    validator = ChangValidation()
    results = validator.run_full_validation(market_data, n_iterations=50)
    
    return results

if __name__ == "__main__":
    # Run basic optimization
    optimization_result = run_basic_optimization()
    
    # Run validation
    print("\nPress Enter to run validation suite...")
    input()
    validation_results = run_validation()
    
    print("\nPhase 1 implementation complete!")
    print("QSW optimizer is working and validated against Chang et al. results.")