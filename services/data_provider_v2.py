"""
Unified Market Data Provider Service

Supports multiple data providers with automatic fallback:
- yfinance (default, free)
- Alpaca (free tier available, real-time)
- Polygon (paid, high-quality)

Configuration via environment variables:
    DATA_PROVIDER: Primary provider (yfinance, alpaca, polygon)
    ALPACA_API_KEY: Alpaca API key
    ALPACA_API_SECRET: Alpaca API secret
    ALPACA_BASE_URL: Alpaca API URL (https://data.alpaca.markets)
    POLYGON_API_KEY: Polygon API key
    POLYGON_BASE_URL: Polygon API URL (https://api.polygon.io)
    DATA_PROVIDER_FALLBACK: Enable fallback to next provider on failure (true/false)

Usage:
    from services.data_provider_v2 import MarketDataProvider
    
    provider = MarketDataProvider()
    data = provider.fetch_market_data(['AAPL', 'MSFT'], start_date='2023-01-01', end_date='2023-12-31')
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    def fetch_prices(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch adjusted close prices for tickers."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass


class YfinanceProvider(DataProvider):
    """yfinance data provider (default, free)."""
    
    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
            self._available = True
        except ImportError:
            self._available = False
    
    def get_name(self) -> str:
        return "yfinance"
    
    def is_available(self) -> bool:
        return self._available
    
    def fetch_prices(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch adjusted close prices from yfinance."""
        import yfinance as yf
        
        data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            progress=False,
            group_by='ticker'
        )
        
        # Extract adjusted close prices
        if isinstance(data.columns, pd.MultiIndex):
            prices = {}
            for ticker in tickers:
                if (ticker, 'Adj Close') in data.columns:
                    prices[ticker] = data[(ticker, 'Adj Close')]
                elif (ticker, 'Close') in data.columns:
                    prices[ticker] = data[(ticker, 'Close')]
            
            if prices:
                return pd.DataFrame(prices)
            else:
                raise ValueError("No price data found")
        elif 'Adj Close' in data.columns:
            return data['Adj Close'].to_frame() if isinstance(data, pd.DataFrame) else data
        else:
            return data


class AlpacaProvider(DataProvider):
    """Alpaca data provider (free tier, real-time)."""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY', '')
        self.api_secret = os.getenv('ALPACA_API_SECRET', '')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://data.alpaca.markets')
        self._available = bool(self.api_key and self.api_secret)
        
        if self._available:
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockBarsRequest
                from alpaca.data.timeframe import TimeFrame
                self._client = StockHistoricalDataClient(self.api_key, self.api_secret)
                self._available = True
            except ImportError:
                self._available = False
                logger.warning("Alpaca SDK not installed. Install with: pip install alpaca-py")
    
    def get_name(self) -> str:
        return "Alpaca"
    
    def is_available(self) -> bool:
        return self._available
    
    def fetch_prices(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch adjusted close prices from Alpaca."""
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        
        request_params = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = self._client.get_stock_bars(request_params)
        
        # Convert to DataFrame
        data = bars.df
        
        if data.empty:
            raise ValueError("No data returned from Alpaca")
        
        # Pivot to get prices by ticker
        prices = data['close'].unstack(level=0)
        
        return prices


class PolygonProvider(DataProvider):
    """Polygon.io data provider (paid, high-quality)."""
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY', '')
        self.base_url = os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io')
        self._available = bool(self.api_key)
        
        if self._available:
            try:
                from polygon import RESTClient
                self._client = RESTClient(self.api_key)
                self._available = True
            except ImportError:
                self._available = False
                logger.warning("Polygon SDK not installed. Install with: pip install polygon-api-client")
    
    def get_name(self) -> str:
        return "Polygon"
    
    def is_available(self) -> bool:
        return self._available
    
    def fetch_prices(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Fetch adjusted close prices from Polygon."""
        from polygon import RESTClient
        
        prices = {}
        
        for ticker in tickers:
            try:
                # Fetch aggregates (daily bars)
                aggs = self._client.get_aggs(
                    ticker=ticker,
                    multiplier=1,
                    timespan='day',
                    from_date=start_date,
                    to_date=end_date
                )
                
                if aggs:
                    ticker_data = {
                        'date': [agg.timestamp for agg in aggs],
                        'close': [agg.close for agg in aggs]
                    }
                    df = pd.DataFrame(ticker_data)
                    df.set_index('date', inplace=True)
                    prices[ticker] = df['close']
                    
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker} from Polygon: {e}")
        
        if not prices:
            raise ValueError("No data returned from Polygon")
        
        return pd.DataFrame(prices)


class MarketDataProvider:
    """
    Unified market data provider with automatic fallback.
    
    Supports:
    - Multiple providers (yfinance, Alpaca, Polygon)
    - Automatic fallback on failure
    - Consistent output format
    - Provider selection via environment variable
    """
    
    def __init__(self, provider: Optional[str] = None, fallback: bool = True):
        """
        Initialize market data provider.
        
        Args:
            provider: Primary provider name (yfinance, alpaca, polygon)
            fallback: Enable automatic fallback to next available provider
        """
        self.fallback_enabled = fallback
        
        # Initialize providers
        self._providers: Dict[str, DataProvider] = {
            'yfinance': YfinanceProvider(),
            'alpaca': AlpacaProvider(),
            'polygon': PolygonProvider(),
        }
        
        # Select primary provider
        if provider:
            self.primary_provider = provider.lower()
        else:
            self.primary_provider = os.getenv('DATA_PROVIDER', 'yfinance').lower()
        
        # Validate provider
        if self.primary_provider not in self._providers:
            logger.warning(f"Unknown provider '{self.primary_provider}', using yfinance")
            self.primary_provider = 'yfinance'
        
        logger.info(f"Market data provider initialized: primary={self.primary_provider}, fallback={self.fallback_enabled}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (configured) providers."""
        return [name for name, provider in self._providers.items() if provider.is_available()]
    
    def _get_provider_order(self) -> List[str]:
        """Get ordered list of providers to try."""
        order = [self.primary_provider]
        
        if self.fallback_enabled:
            # Add remaining providers in order of preference
            fallback_order = ['yfinance', 'alpaca', 'polygon']
            for p in fallback_order:
                if p != self.primary_provider and p not in order:
                    order.append(p)
        
        return order
    
    def fetch_market_data(
        self,
        tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y"
    ) -> Dict:
        """
        Fetch market data using configured provider with fallback.
        
        Args:
            tickers: List of stock tickers
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            period: Default period if dates not provided
            
        Returns:
            Dictionary with market data
        """
        # Set default dates
        if not start_date and not end_date:
            end_date = datetime.today().strftime('%Y-%m-%d')
            start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        elif not end_date:
            end_date = datetime.today().strftime('%Y-%m-%d')
        elif not start_date:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
        
        logger.info(f"Fetching data from {start_date} to {end_date} using {self.primary_provider}")
        
        # Try providers in order
        last_error = None
        provider_order = self._get_provider_order()
        
        for provider_name in provider_order:
            provider = self._providers.get(provider_name)
            
            if not provider or not provider.is_available():
                logger.debug(f"Provider {provider_name} not available, skipping")
                continue
            
            try:
                logger.info(f"Trying {provider_name}...")
                prices = provider.fetch_prices(tickers, start_date, end_date)
                
                # Process prices into standard format
                return self._process_prices(prices, tickers, start_date, end_date, provider_name)
                
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                last_error = e
                
                if not self.fallback_enabled:
                    raise
        
        # All providers failed
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def _process_prices(
        self,
        prices: pd.DataFrame,
        tickers: List[str],
        start_date: str,
        end_date: str,
        provider_name: str
    ) -> Dict:
        """Process price data into standard format."""
        # Clean up prices DataFrame
        prices = prices.dropna(axis=1, how='all')
        
        if prices.empty:
            raise ValueError("No valid price data found")
        
        # Calculate returns
        returns_df = prices.pct_change().dropna()
        
        if returns_df.empty:
            raise ValueError("Not enough data points to calculate returns")
        
        # Calculate annualized returns
        annual_returns = returns_df.mean() * 252
        
        # Calculate annualized covariance matrix
        from services.risk_models import ledoit_wolf_covariance
        annual_cov_np = ledoit_wolf_covariance(returns_df.values, annualize=True)
        annual_cov = pd.DataFrame(annual_cov_np, index=returns_df.columns, columns=returns_df.columns)
        
        # Get metadata
        from services.market_data import get_asset_metadata
        metadata = get_asset_metadata(list(prices.columns))
        
        # Build result
        assets_list = list(prices.columns)
        
        result = {
            "assets": assets_list,
            "names": [metadata.get(asset, {}).get('name', asset) for asset in assets_list],
            "sectors": [metadata.get(asset, {}).get('sector', 'Unknown') for asset in assets_list],
            "returns": annual_returns.values.astype(float).tolist(),
            "covariance": annual_cov.values.astype(float).tolist(),
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(returns_df),
            "provider": provider_name,
            "success": True,
            "message": f"Successfully fetched data for {len(assets_list)} assets from {provider_name}"
        }
        
        logger.info(f"Successfully processed market data from {provider_name} for {len(assets_list)} assets")
        return result
    
    def fetch_metadata(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Fetch asset metadata without price data.
        
        Args:
            tickers: List of tickers
            
        Returns:
            Dictionary mapping tickers to metadata
        """
        from services.market_data import get_asset_metadata
        return get_asset_metadata(tickers)


# Convenience function for backward compatibility
def fetch_market_data(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "1y"
) -> Dict:
    """
    Fetch market data (backward compatible function).
    
    Uses unified provider with fallback.
    """
    provider = MarketDataProvider()
    return provider.fetch_market_data(tickers, start_date, end_date, period)


if __name__ == "__main__":
    # Example usage
    print("Testing unified market data provider...")
    
    provider = MarketDataProvider()
    print(f"Available providers: {provider.get_available_providers()}")
    
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    try:
        data = provider.fetch_market_data(tickers, period="1mo")
        print(f"\n✅ Success! Provider used: {data.get('provider')}")
        print(f"Assets: {data['assets']}")
        print(f"Returns: {data['returns']}")
    except Exception as e:
        print(f"❌ Error: {e}")
