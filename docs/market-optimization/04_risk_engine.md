# Risk Engine

## Purpose

The risk engine should move the project beyond simple Sharpe maximization.

A robust optimizer should evaluate:

- Volatility
- Tail risk
- Drawdown risk
- Concentration risk
- Turnover risk
- Factor exposure
- Regime sensitivity

## Target structure

```text
services/risk/
  covariance.py
  shrinkage.py
  cvar.py
  cdar.py
  drawdown.py
  factor_exposure.py
  regime.py
  schema.py
```

## Risk model inventory

| Model | Algorithm type | Use case |
|---|---|---|
| Sample covariance | Statistical estimator | Baseline covariance |
| Ledoit-Wolf | Shrinkage covariance estimator | Stable covariance under noisy data |
| OAS | Shrinkage covariance estimator | Alternative stable covariance estimate |
| EWMA covariance | Exponentially weighted estimator | More weight on recent market behavior |
| CVaR | Tail-risk estimator | Average loss beyond VaR |
| CDaR | Drawdown-risk estimator | Average severe drawdown |
| Semivariance | Downside-risk estimator | Penalize downside moves only |
| Herfindahl index | Concentration metric | Detect overconcentration |
| Beta exposure | Factor model | Market sensitivity |
| Regime label | Classification / clustering | Bull, bear, high-vol, low-vol states |

## Risk summary schema

```python
from dataclasses import dataclass
import pandas as pd


@dataclass
class RiskSummary:
    volatility: float
    annualized_return: float
    sharpe: float
    sortino: float
    cvar_95: float
    var_95: float
    max_drawdown: float
    concentration_hhi: float
    turnover: float
    beta: float | None
    regime: str | None
    covariance_method: str
```

## Covariance shrinkage

```python
import pandas as pd
from sklearn.covariance import LedoitWolf, OAS


def estimate_covariance(
    returns: pd.DataFrame,
    method: str = "ledoit_wolf",
) -> pd.DataFrame:
    clean = returns.dropna()

    if method == "sample":
        cov = clean.cov().values
    elif method == "ledoit_wolf":
        cov = LedoitWolf().fit(clean.values).covariance_
    elif method == "oas":
        cov = OAS().fit(clean.values).covariance_
    else:
        raise ValueError(f"Unknown covariance method: {method}")

    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)
```

Algorithm type:

- **Sample covariance:** classical statistical estimator
- **Ledoit-Wolf:** shrinkage estimator
- **OAS:** shrinkage estimator optimized under Gaussian assumptions

## CVaR

```python
import numpy as np
import pandas as pd


def portfolio_cvar(
    returns: pd.DataFrame,
    weights: np.ndarray,
    alpha: float = 0.95,
) -> float:
    portfolio_returns = returns.dropna().values @ weights
    losses = -portfolio_returns
    var = np.quantile(losses, alpha)
    tail_losses = losses[losses >= var]
    return float(tail_losses.mean())
```

Algorithm type:

- Historical simulation expected shortfall / CVaR

## Drawdown

```python
def max_drawdown(portfolio_returns: pd.Series) -> float:
    equity = (1 + portfolio_returns).cumprod()
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return float(drawdown.min())
```

Algorithm type:

- Path-dependent risk metric

## Concentration

```python
def herfindahl_hirschman_index(weights: dict[str, float]) -> float:
    return float(sum(w ** 2 for w in weights.values()))
```

Interpretation:

| HHI | Meaning |
|---:|---|
| Near `1 / n` | Diversified |
| `> 0.20` | Concentrated |
| `> 0.35` | Highly concentrated |

## Regime tagging

Initial simple version:

```python
def classify_regime(
    benchmark_returns: pd.Series,
    volatility_window: int = 21,
) -> str:
    trailing_return = benchmark_returns.tail(63).sum()
    trailing_vol = benchmark_returns.tail(volatility_window).std()

    long_vol = benchmark_returns.std()

    if trailing_return > 0 and trailing_vol <= long_vol:
        return "bull_low_vol"
    if trailing_return > 0 and trailing_vol > long_vol:
        return "bull_high_vol"
    if trailing_return <= 0 and trailing_vol <= long_vol:
        return "bear_low_vol"
    return "bear_high_vol"
```

Algorithm type:

- Rule-based regime classifier

Later upgrade:

- Hidden Markov Model
- Gaussian Mixture Model
- Change-point detection
- Volatility clustering

## Dashboard risk panel

The dashboard should display:

```text
Risk Breakdown
  Annualized Return
  Volatility
  Sharpe
  Sortino
  CVaR 95
  Max Drawdown
  Concentration HHI
  Turnover
  Regime
  Top factor exposures
```

## Acceptance criteria

The risk engine is complete when:

- Every optimizer result includes a `RiskSummary`
- CVaR and max drawdown are shown beside Sharpe
- Covariance method is logged
- Concentration warnings are emitted
- Regime label is stored in the experiment metadata
