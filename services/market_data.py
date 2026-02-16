"""
Market data service for portfolio optimization
Fetches real market data using yfinance and computes returns/covariance
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_market_data(
    tickers: List[str], 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    period: str = "1y"  # Default to 1 year if no dates provided
) -> Dict:
    """
    Fetch market data for given tickers and compute returns/covariance.
    
    Args:
        tickers: List of stock tickers (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        start_date: Start date in YYYY-MM-DD format (optional if period is provided)
        end_date: End date in YYYY-MM-DD format (optional if period is provided)
        period: Data period if dates not provided (e.g., '1y', '2y', '5y', 'max')
    
    Returns:
        Dictionary with market data including returns, covariance, and metadata
    """
    logger.info(f"Fetching market data for tickers: {tickers}")
    
    if not tickers:
        raise ValueError("Tickers list cannot be empty")
    
    # Validate tickers
    for ticker in tickers:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError(f"Invalid ticker: {ticker}")
    
    # Set default dates if not provided
    if not start_date and not end_date:
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    elif not end_date:
        end_date = datetime.today().strftime('%Y-%m-%d')
    elif not start_date:
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
    
    logger.info(f"Fetching data from {start_date} to {end_date}")
    
    try:
        # Download data using yfinance
        data = yf.download(
            tickers, 
            start=start_date, 
            end=end_date,
            progress=False,
            group_by='ticker'
        )
        
        # Handle case where only one ticker is provided
        if len(tickers) == 1:
            ticker = tickers[0]
            if isinstance(data.columns, pd.MultiIndex):
                # Multi-column case (when downloading multiple assets but only one ticker was valid)
                if ticker in data.columns.levels[0]:
                    data = data[ticker]
                else:
                    # If the ticker doesn't exist in the data, try to get it directly
                    single_ticker_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                    if single_ticker_data.empty:
                        raise ValueError(f"No data found for ticker: {ticker}")
                    data = single_ticker_data
            else:
                # Single column case
                data = data
        else:
            # Multi-ticker case - ensure we have data for each ticker
            if isinstance(data.columns, pd.MultiIndex):
                # Data is organized as (Ticker, OHLCV)
                available_tickers = set()
                for col in data.columns:
                    if len(col) > 0:
                        available_tickers.add(col[0])
                
                # Check if we got data for all requested tickers
                missing_tickers = set(tickers) - available_tickers
                if missing_tickers:
                    logger.warning(f"Missing data for tickers: {missing_tickers}")
                    # Remove missing tickers from further processing
                    tickers = [t for t in tickers if t not in missing_tickers]
                    if not tickers:
                        raise ValueError("No valid tickers found in the provided date range")
                    
                    # Extract data only for available tickers
                    ticker_data = {}
                    for ticker in tickers:
                        if ticker in data.columns.levels[0]:
                            ticker_data[ticker] = data[ticker]['Adj Close']
                    
                    # Combine into a single DataFrame
                    combined_data = pd.DataFrame(ticker_data)
                    data = combined_data
            else:
                # Single ticker case where data is already a Series/DataFrame
                if len(tickers) == 1:
                    data = pd.DataFrame({tickers[0]: data['Adj Close'] if 'Adj Close' in data.columns else data})
                else:
                    # Multiple tickers but data structure is unexpected
                    raise ValueError("Unexpected data structure from yfinance")
        
        # Handle MultiIndex columns (ticker, OHLCV format)
        if isinstance(data.columns, pd.MultiIndex):
            # Extract 'Adj Close' for each ticker if available
            close_prices = {}
            for ticker in tickers:
                if (ticker, 'Adj Close') in data.columns:
                    close_prices[ticker] = data[(ticker, 'Adj Close')]
                elif (ticker, 'Close') in data.columns:
                    close_prices[ticker] = data[(ticker, 'Close')]
                else:
                    # If we can't find close prices for this ticker, try to get any available data
                    ticker_cols = [col for col in data.columns if col[0] == ticker]
                    if ticker_cols:
                        # Use 'Close' if available, otherwise use 'Adj Close', otherwise first available
                        close_col = None
                        for col_name in ['Close', 'Adj Close']:
                            for col in ticker_cols:
                                if col[1] == col_name:
                                    close_col = col
                                    break
                            if close_col:
                                break
                        if not close_col and ticker_cols:
                            close_col = ticker_cols[0]  # Use first available column
                        
                        if close_col:
                            close_prices[ticker] = data[close_col]
            
            if close_prices:
                prices = pd.DataFrame(close_prices)
            else:
                # Fallback: try to get data differently
                prices = data.xs('Close', level=1, axis=1, drop_level=False) if 'Close' in data.columns.get_level_values(1) else data
                if isinstance(prices.columns, pd.MultiIndex):
                    prices = prices.droplevel(1)  # Keep only ticker names as columns
        elif 'Adj Close' in data.columns:
            prices = data['Adj Close'].copy()
        elif isinstance(data, pd.Series):
            # Single ticker case where data is a Series
            prices = pd.DataFrame({tickers[0]: data})
        else:
            # Assume data is already the price DataFrame
            prices = data.copy()

        # If prices still has MultiIndex columns, extract just the ticker names
        if isinstance(prices.columns, pd.MultiIndex):
            # Extract only the ticker names from the MultiIndex
            prices.columns = [col[0] for col in prices.columns]
            # Remove duplicate columns if any
            prices = prices.loc[:, ~prices.columns.duplicated()]
        
        # If prices is still a Series, convert to DataFrame
        if isinstance(prices, pd.Series):
            prices = pd.DataFrame({prices.name or tickers[0]: prices})
        
        # Drop any columns that are all NaN
        prices = prices.dropna(axis=1, how='all')
        
        if prices.empty:
            raise ValueError("No valid price data found for the given tickers and date range")
        
        # Calculate returns
        returns_df = prices.pct_change().dropna()
        
        if returns_df.empty:
            raise ValueError("Not enough data points to calculate returns")
        
        # Calculate annualized returns
        annual_returns = returns_df.mean() * 252  # 252 trading days per year
        
        # Calculate annualized covariance matrix (Ledoit-Wolf shrinkage)
        from services.risk_models import ledoit_wolf_covariance
        annual_cov_np = ledoit_wolf_covariance(returns_df.values, annualize=True)
        annual_cov = pd.DataFrame(annual_cov_np, index=returns_df.columns, columns=returns_df.columns)
        
        # Get company info for sectors (where available)
        sectors = {}
        names = {}
        
        for ticker in prices.columns:
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                sectors[ticker] = info.get('sector', 'Unknown')
                names[ticker] = info.get('longName', ticker)
            except Exception as e:
                logger.warning(f"Could not fetch info for {ticker}: {e}")
                sectors[ticker] = 'Unknown'
                names[ticker] = ticker
        
        # Convert to lists/arrays for JSON serialization
        assets_list = list(prices.columns)
        returns_array = annual_returns.values.astype(float).tolist()
        cov_matrix = annual_cov.values.astype(float).tolist()
        
        # Validate data
        if len(assets_list) != len(returns_array):
            raise ValueError("Mismatch between assets and returns")
        
        if len(cov_matrix) != len(returns_array) or any(len(row) != len(returns_array) for row in cov_matrix):
            raise ValueError("Covariance matrix dimensions don't match returns")
        
        result = {
            "assets": assets_list,
            "names": [names.get(asset, asset) for asset in assets_list],
            "sectors": [sectors.get(asset, "Unknown") for asset in assets_list],
            "returns": returns_array,
            "covariance": cov_matrix,
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(returns_df),
            "success": True,
            "message": f"Successfully fetched data for {len(assets_list)} assets"
        }
        
        logger.info(f"Successfully processed market data for {len(assets_list)} assets")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        raise ValueError(f"Failed to fetch market data: {str(e)}")


def validate_tickers(tickers: List[str]) -> List[str]:
    """
    Validate and clean ticker list.
    
    Args:
        tickers: List of potential tickers
        
    Returns:
        List of validated tickers
    """
    validated = []
    for ticker in tickers:
        # Clean ticker string
        clean_ticker = ticker.strip().upper()
        if clean_ticker and len(clean_ticker) <= 10:  # Reasonable ticker length
            validated.append(clean_ticker)
    
    return validated


def get_asset_metadata(tickers: List[str]) -> Dict[str, Dict]:
    """
    Get metadata for assets (sector, name, etc.) without full price data.
    
    Args:
        tickers: List of stock tickers
        
    Returns:
        Dictionary mapping tickers to their metadata
    """
    metadata = {}
    
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            metadata[ticker] = {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', None),
                'currency': info.get('currency', 'USD')
            }
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {ticker}: {e}")
            metadata[ticker] = {
                'name': ticker,
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': None,
                'currency': 'USD'
            }
    
    return metadata


if __name__ == "__main__":
    # Example usage
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    try:
        data = fetch_market_data(tickers, period="1y")
        print(f"Successfully fetched data for {len(data['assets'])} assets")
        print(f"Assets: {data['assets']}")
        print(f"Returns: {data['returns']}")
        print(f"Shape of covariance matrix: {len(data['covariance'])}x{len(data['covariance'][0])}")
    except Exception as e:
        print(f"Error: {e}")