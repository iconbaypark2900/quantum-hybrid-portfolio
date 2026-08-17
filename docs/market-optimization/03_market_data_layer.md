# Market Data Layer

## Purpose

The market data layer should make the optimizer trustworthy.

A portfolio optimizer can be mathematically sophisticated and still fail if:

- Prices are stale
- Splits are not adjusted
- Missing values are silently forward-filled
- Corporate actions are mishandled
- Data vendors disagree
- Tickers are delisted or renamed
- Backtest uses data unavailable at the decision date

## Target design

```text
services/market_data/
  base.py
  tiingo_provider.py
  yfinance_provider.py
  cache.py
  validation.py
  corporate_actions.py
```

## Provider abstraction

```python
from dataclasses import dataclass
from typing import Protocol
import pandas as pd


@dataclass(frozen=True)
class MarketDataRequest:
    tickers: list[str]
    start: str
    end: str
    adjusted: bool = True


class MarketDataProvider(Protocol):
    name: str

    def get_prices(self, request: MarketDataRequest) -> pd.DataFrame:
        ...
```

## Service layer

```python
class MarketDataService:
    def __init__(self, providers: list[MarketDataProvider]):
        self.providers = providers

    def get_validated_prices(self, request: MarketDataRequest) -> pd.DataFrame:
        errors = []

        for provider in self.providers:
            try:
                prices = provider.get_prices(request)
                validate_price_panel(prices, request)
                return prices
            except Exception as exc:
                errors.append((provider.name, str(exc)))

        raise RuntimeError(f"All market data providers failed: {errors}")
```

## Recommended provider order

| Priority | Provider | Role |
|---:|---|---|
| 1 | Tiingo | Primary provider |
| 2 | yfinance | Fallback and demo mode |
| 3 | Local cache | Reproducibility and offline experiments |
| 4 | Synthetic generator | CI and tests |

## Validation checks

```python
import pandas as pd


def validate_price_panel(prices: pd.DataFrame, request: MarketDataRequest) -> None:
    missing_cols = set(request.tickers) - set(prices.columns)
    if missing_cols:
        raise ValueError(f"Missing tickers: {missing_cols}")

    if not prices.index.is_monotonic_increasing:
        raise ValueError("Price index must be sorted")

    if prices.empty:
        raise ValueError("Price panel is empty")

    if (prices <= 0).any().any():
        raise ValueError("Prices must be positive")

    missing_ratio = prices.isna().mean().max()
    if missing_ratio > 0.05:
        raise ValueError(f"Too much missing data: {missing_ratio:.2%}")

    stale_ratio = prices.pct_change().eq(0).mean().max()
    if stale_ratio > 0.20:
        raise ValueError(f"Possible stale data: {stale_ratio:.2%}")
```

## Validation report

Each data request should produce a report:

```json
{
  "provider": "tiingo",
  "tickers": ["NVDA", "AMD", "MSFT"],
  "start": "2023-01-01",
  "end": "2026-06-01",
  "trading_days": 857,
  "missing_by_ticker": {
    "NVDA": 0,
    "AMD": 0,
    "MSFT": 0
  },
  "max_missing_ratio": 0.0,
  "stale_price_warnings": [],
  "adjusted": true,
  "cache_hit": false
}
```

## Cache design

```text
data/cache/
  prices/
    tiingo/
      NVDA_2023-01-01_2026-06-01_adjusted.parquet
  validation_reports/
    2026-06-04T180000Z_tiingo_NVDA_AMD_MSFT.json
```

Use Parquet for price panels.

## Return engineering

```python
def compute_returns(
    prices: pd.DataFrame,
    method: str = "log",
) -> pd.DataFrame:
    if method == "log":
        return np.log(prices / prices.shift(1)).dropna()
    if method == "simple":
        return prices.pct_change().dropna()
    raise ValueError(f"Unknown return method: {method}")
```

## Testing targets

### `tests/test_market_data_validation.py`

Test cases:

- Missing ticker column raises
- Non-monotonic date index raises
- Negative or zero price raises
- Too many NaNs raises
- Empty panel raises
- Valid panel passes
- Provider fallback works
- Cache roundtrip preserves data

## Acceptance criteria

The market data layer is complete when:

- Tiingo and yfinance share the same interface
- Every optimization run stores a data validation report
- No optimizer can run on unvalidated prices
- Tests cover missing, stale, invalid, and empty data
- Dashboard can show data quality before allocation
