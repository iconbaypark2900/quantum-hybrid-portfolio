"""
Market data service for portfolio optimization.

The primary ``fetch_market_data`` entry point now delegates to
``services.data_provider_v2`` which supports Tiingo (recommended),
yfinance (legacy fallback), Alpaca, and Polygon.

``get_asset_metadata`` retains the yfinance-backed implementation as a
best-effort fallback used by data_provider_v2 for non-Tiingo providers.

Tiingo runs resolve name/exchange from the Tiingo daily metadata endpoint.
Sector/industry are not on that endpoint; optionally merge **only** those
fields from yfinance when ``METADATA_SECTOR_SOURCE=yfinance`` (see
``get_yfinance_sector_industry``).
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_market_data(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "1y",
) -> Dict:
    """Fetch market data for given tickers and compute returns/covariance.

    Delegates to ``services.data_provider_v2`` which selects the configured
    provider (Tiingo by default when TIINGO_API_KEY is set).

    Args:
        tickers: List of stock tickers (e.g. ['AAPL', 'MSFT', 'GOOGL']).
        start_date: Start date YYYY-MM-DD (optional when period given).
        end_date: End date YYYY-MM-DD (optional when period given).
        period: Lookback period used when dates are omitted (e.g. '1y').

    Returns:
        Dict with keys: assets, names, sectors, returns, covariance,
        start_date, end_date, data_points, provider, success, message.
    """
    logger.info("fetch_market_data delegating to data_provider_v2 for tickers: %s", tickers)
    from services.data_provider_v2 import fetch_market_data as _v2_fetch
    return _v2_fetch(tickers, start_date, end_date, period)


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


def get_yfinance_sector_industry(tickers: List[str]) -> Dict[str, Dict[str, str]]:
    """Return sector and industry per ticker from yfinance (no other fields).

    Used to enrich Tiingo-backed metadata when ``METADATA_SECTOR_SOURCE=yfinance``.
    Network-bound; callers should enable only when acceptable.
    """
    out: Dict[str, Dict[str, str]] = {}
    for ticker in tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            out[ticker] = {
                "sector": info.get("sector") or "Unknown",
                "industry": info.get("industry") or "Unknown",
            }
        except Exception as e:
            logger.warning("yfinance sector/industry failed for %s: %s", ticker, e)
            out[ticker] = {"sector": "Unknown", "industry": "Unknown"}
    return out


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