"""
Backtesting service for portfolio optimization
Performs rolling window backtesting of portfolio strategies
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import yfinance as yf
from dateutil.relativedelta import relativedelta
import logging

from config.qsw_config import QSWConfig
from services.market_data import fetch_market_data, get_asset_metadata
from services.portfolio_optimizer import run_optimization, get_config_for_preset
from services.constraints import PortfolioConstraints

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_backtest(
    tickers: List[str],
    start_date: str,
    end_date: str,
    rebalance_frequency: str = "monthly",  # "weekly", "monthly", "quarterly", "yearly"
    objective: str = "max_sharpe",
    target_return: Optional[float] = None,
    strategy_preset: str = "balanced",
    constraints: Optional[PortfolioConstraints] = None,
    **optimization_params
) -> Dict:
    """
    Run a backtest of portfolio optimization strategy.
    
    Args:
        tickers: List of stock tickers to include in portfolio
        start_date: Start date for backtest (YYYY-MM-DD)
        end_date: End date for backtest (YYYY-MM-DD)
        rebalance_frequency: How often to rebalance ("weekly", "monthly", "quarterly", "yearly")
        objective: Optimization objective ("max_sharpe", "min_variance", "target_return", "risk_parity")
        target_return: Target return for target_return objective
        **optimization_params: Additional parameters for optimization (omega, evolution_time, etc.)
    
    Returns:
        Dictionary with backtest results including equity curve and metrics
    """
    logger.info(f"Starting backtest for {len(tickers)} assets from {start_date} to {end_date}")
    
    # Validate inputs
    if not tickers:
        raise ValueError("Tickers list cannot be empty")
    
    if len(tickers) < 2:
        raise ValueError("Need at least 2 assets for portfolio optimization")
    
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start_dt >= end_dt:
        raise ValueError("Start date must be before end date")
    
    # Define rebalance periods based on frequency
    rebalance_periods = _get_rebalance_dates(start_dt, end_dt, rebalance_frequency)
    
    # Download full price history
    logger.info(f"Downloading price history for {len(tickers)} tickers")
    full_data = yf.download(
        tickers,
        start=start_dt.strftime("%Y-%m-%d"),
        end=end_dt.strftime("%Y-%m-%d"),
        progress=False,
        group_by='ticker'
    )
    
    # Handle single ticker case
    if len(tickers) == 1:
        ticker = tickers[0]
        if isinstance(full_data.columns, pd.MultiIndex):
            if ticker in full_data.columns.levels[0]:
                full_data = full_data[ticker]
            else:
                single_ticker_data = yf.download(ticker, start=start_dt, end=end_dt, progress=False)
                full_data = single_ticker_data
        else:
            full_data = full_data
    
    # Ensure we have price data
    if isinstance(full_data.columns, pd.MultiIndex):
        # Multi-ticker case - extract Adjusted Close prices
        # With group_by='ticker', columns are (Ticker, Attr); use xs to select Attr
        if 'Adj Close' in full_data.columns.levels[1]:
            prices = full_data.xs('Adj Close', axis=1, level=1).copy()
        elif 'Adj Close' in full_data.columns.levels[0]:
            prices = full_data.xs('Adj Close', axis=1, level=0).copy()
        else:
            # Try to get Close prices if Adj Close not available
            if 'Close' in full_data.columns.levels[1]:
                prices = full_data.xs('Close', axis=1, level=1).copy()
            elif 'Close' in full_data.columns.levels[0]:
                prices = full_data.xs('Close', axis=1, level=0).copy()
            else:
                raise ValueError("Could not find price data in expected format")
    else:
        # Single ticker case
        if 'Adj Close' in full_data.columns:
            prices = full_data[['Adj Close']].copy()
            prices.columns = [tickers[0]]
        elif 'Close' in full_data.columns:
            prices = full_data[['Close']].copy()
            prices.columns = [tickers[0]]
        else:
            prices = full_data.copy()
    
    # Remove any columns that are all NaN
    prices = prices.dropna(axis=1, how='all')
    
    if prices.empty:
        raise ValueError("No valid price data found for the given tickers and date range")
    
    # Ensure all requested tickers have data
    available_tickers = [col for col in prices.columns if col in tickers]
    missing_tickers = set(tickers) - set(available_tickers)
    if missing_tickers:
        logger.warning(f"Missing data for tickers: {missing_tickers}")
        tickers = available_tickers
        if not tickers:
            raise ValueError("No valid tickers found in the provided date range")
    
    # Sort prices by date
    prices = prices.sort_index()

    # Fetch sector metadata for constraints (Phase 2)
    try:
        sector_metadata = get_asset_metadata(tickers)
    except Exception as e:
        logger.warning(f"Could not fetch sector metadata: {e}")
        sector_metadata = {}
    
    # Initialize backtest results
    backtest_results = []
    cumulative_value = 100.0  # Start with $100
    current_weights = None
    
    logger.info(f"Starting backtest with {len(rebalance_periods)} rebalance periods")
    
    for i, rebalance_date in enumerate(rebalance_periods):
        logger.info(f"Processing rebalance {i+1}/{len(rebalance_periods)} at {rebalance_date}")
        
        # Define lookback period for calculating returns/covariance
        lookback_start = rebalance_date - relativedelta(years=1)  # Use 1 year lookback
        
        # Get data for lookback period
        lookback_data = prices[(prices.index >= lookback_start) & (prices.index <= rebalance_date)]
        
        if lookback_data.shape[0] < 22:  # Require at least ~1 month of data
            logger.warning(f"Not enough data for rebalance at {rebalance_date}, skipping")
            continue
        
        # Calculate returns for lookback period
        returns_data = lookback_data.pct_change().dropna()
        
        if returns_data.empty or returns_data.shape[0] < 22:
            logger.warning(f"Not enough return data for rebalance at {rebalance_date}, skipping")
            continue
        
        # Calculate annualized returns and covariance (Ledoit-Wolf shrinkage)
        from services.risk_models import ledoit_wolf_covariance
        annual_returns = returns_data.mean() * 252
        annual_cov_np = ledoit_wolf_covariance(returns_data.values, annualize=True)
        annual_cov = pd.DataFrame(annual_cov_np, index=returns_data.columns, columns=returns_data.columns)
        
        # Ensure we have data for all tickers
        valid_tickers = [t for t in tickers if t in annual_returns.index and t in annual_cov.columns]
        if len(valid_tickers) < 2:
            logger.warning(f"Not enough valid tickers for rebalance at {rebalance_date}, skipping")
            continue
        
        # Filter to valid tickers
        filtered_returns = annual_returns[valid_tickers].values
        filtered_cov = annual_cov.loc[valid_tickers, valid_tickers].values
        
        # Run optimization
        sectors_list = [sector_metadata.get(t, {}).get('sector', 'Unknown') for t in valid_tickers]
        try:
            weights = _run_optimization(
                returns=filtered_returns,
                covariance=filtered_cov,
                valid_tickers=valid_tickers,
                objective=objective,
                target_return=target_return,
                strategy_preset=strategy_preset,
                constraints=constraints or PortfolioConstraints(),
                sectors=sectors_list,
                **optimization_params
            )
        except Exception as e:
            logger.error(f"Optimization failed at {rebalance_date}: {e}")
            continue
        
        # Determine next rebalance date
        if i < len(rebalance_periods) - 1:
            next_rebalance = rebalance_periods[i + 1]
        else:
            next_rebalance = end_dt
        
        # Get returns for the period from rebalance_date to next_rebalance
        period_prices = prices[(prices.index > rebalance_date) & (prices.index <= next_rebalance)]
        if period_prices.empty:
            continue
            
        period_returns = period_prices.pct_change().dropna()
        
        # Align weights with actual tickers in the period returns
        weight_mapping = {valid_tickers[i]: weights[i] for i in range(len(valid_tickers))}
        
        # Calculate portfolio returns for each period
        portfolio_returns = []
        for date, row in period_returns.iterrows():
            # Calculate portfolio return for this date
            valid_assets_returns = []
            valid_weights = []
            
            for ticker in valid_tickers:
                if ticker in row.index and not pd.isna(row[ticker]):
                    valid_assets_returns.append(row[ticker])
                    valid_weights.append(weight_mapping[ticker])
            
            if valid_assets_returns and sum(valid_weights) > 0:
                # Normalize weights to sum to 1
                total_weight = sum(valid_weights)
                normalized_weights = [w / total_weight for w in valid_weights]
                
                # Calculate portfolio return
                portfolio_return = sum(ret * weight for ret, weight in zip(valid_assets_returns, normalized_weights))
                portfolio_returns.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'portfolio_return': portfolio_return,
                    'cumulative_value': cumulative_value * (1 + portfolio_return),
                    'weights': {valid_tickers[i]: weight_mapping[valid_tickers[i]] for i in range(len(valid_tickers))}
                })
                cumulative_value *= (1 + portfolio_return)
        
        # Add results for this rebalance period
        if portfolio_returns:
            backtest_results.extend(portfolio_returns)
    
    # Calculate summary metrics
    if backtest_results:
        returns_series = [r['portfolio_return'] for r in backtest_results]
        dates = [r['date'] for r in backtest_results]
        
        # Calculate metrics
        total_return = (backtest_results[-1]['cumulative_value'] / 100.0) - 1
        avg_return = np.mean(returns_series) * 252  # Annualized
        volatility = np.std(returns_series) * np.sqrt(252)  # Annualized
        sharpe_ratio = avg_return / volatility if volatility != 0 else 0
        
        # Calculate max drawdown
        cumulative_values = [r['cumulative_value'] for r in backtest_results]
        running_max = [cumulative_values[0]]
        for value in cumulative_values[1:]:
            running_max.append(max(value, running_max[-1]))
        
        drawdowns = [(cum - mx) / mx for cum, mx in zip(cumulative_values, running_max)]
        max_drawdown = min(drawdowns) if drawdowns else 0
        
        # Calculate other metrics
        winning_months = sum(1 for r in returns_series if r > 0)
        total_months = len(returns_series)
        win_rate = winning_months / total_months if total_months > 0 else 0
        
        summary_metrics = {
            'total_return': total_return,
            'annual_return': avg_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_period_return': (cumulative_values[-1] / cumulative_values[0]) - 1 if cumulative_values else 0,
            'start_date': dates[0] if dates else start_date,
            'end_date': dates[-1] if dates else end_date,
            'num_periods': len(backtest_results)
        }
    else:
        summary_metrics = {
            'total_return': 0,
            'annual_return': 0,
            'volatility': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'total_period_return': 0,
            'start_date': start_date,
            'end_date': end_date,
            'num_periods': 0
        }
    
    result = {
        'results': backtest_results,
        'summary_metrics': summary_metrics,
        'parameters': {
            'tickers': tickers,
            'start_date': start_date,
            'end_date': end_date,
            'rebalance_frequency': rebalance_frequency,
            'objective': objective,
            'target_return': target_return,
            **optimization_params
        }
    }
    
    logger.info(f"Backtest completed. Generated {len(backtest_results)} data points")
    return result


def _get_rebalance_dates(start_date: datetime, end_date: datetime, frequency: str) -> List[datetime]:
    """Generate rebalance dates based on frequency."""
    dates = []
    current_date = start_date
    
    while current_date < end_date:
        dates.append(current_date)
        
        if frequency == "weekly":
            current_date += timedelta(weeks=1)
        elif frequency == "monthly":
            current_date += relativedelta(months=1)
        elif frequency == "quarterly":
            current_date += relativedelta(months=3)
        elif frequency == "yearly":
            current_date += relativedelta(years=1)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
    
    # Add end date if it's not already included
    if dates and dates[-1] < end_date:
        dates.append(end_date)
    
    return dates


def _run_optimization(
    returns: np.ndarray,
    covariance: np.ndarray,
    valid_tickers: List[str],
    objective: str = "max_sharpe",
    target_return: Optional[float] = None,
    strategy_preset: str = "balanced",
    constraints: Optional[PortfolioConstraints] = None,
    sectors: Optional[List[str]] = None,
    **optimization_params
) -> np.ndarray:
    """Run portfolio optimization with specified objective and preset."""
    config = get_config_for_preset(strategy_preset)
    if optimization_params:
        if 'omega' in optimization_params:
            config.default_omega = optimization_params['omega']
        if 'evolution_time' in optimization_params:
            config.evolution_time = optimization_params['evolution_time']
        if 'max_weight' in optimization_params:
            config.max_weight = optimization_params['max_weight']
        if 'max_turnover' in optimization_params:
            config.max_turnover = optimization_params['max_turnover']
    result = run_optimization(
        returns=returns,
        covariance=covariance,
        objective=objective,
        target_return=target_return,
        strategy_preset=strategy_preset,
        config=config,
        constraints=constraints or PortfolioConstraints(),
        asset_names=valid_tickers,
        sectors=sectors or [""] * len(valid_tickers),
    )
    return result.weights


if __name__ == "__main__":
    # Example usage
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    try:
        results = run_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency="monthly",
            objective="max_sharpe"
        )
        
        print(f"Backtest completed with {len(results['results'])} data points")
        print(f"Summary: {results['summary_metrics']}")
    except Exception as e:
        print(f"Backtest failed: {e}")