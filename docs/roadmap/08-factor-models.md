# 08 — Factor Model Integration

**Priority:** Medium  
**Status:** Multiple placeholder stubs in `core/quantum_inspired/` — factor-model weight paths return identity or hardcoded values  
**Area:** Backend `core/quantum_inspired/`, `services/`, `core/portfolio_optimizer.py`

---

## Problem

Several modules in `core/quantum_inspired/` contain explicit placeholder comments where factor model logic should go:

- `advanced_quantum_optimizer.py` line 589: `return weights  # Placeholder - implement based on specific factor model`
- `advanced_quantum_optimizer.py` line 867: `'diversification_ratio': 0.75  # Placeholder`
- `enhanced_quantum_walk.py` line 364: `return weights  # Placeholder - implement based on specific factor model`

Without a real factor model:
- The optimizer has no mechanism to tilt toward known risk premia (value, momentum, quality, low-volatility)
- Factor exposure reporting is absent — users cannot see if their portfolio is accidentally over-exposed to a specific factor
- The "quantum advantage" claim has no classical baseline rooted in a standard factor model to beat

---

## Scope

**In scope:**
- Implement a minimal 4-factor model from return data alone (no external factor database required): **market beta, size, momentum, low-volatility**
- Compute factor loadings from historical returns using OLS regression against factor proxies derived from the asset universe itself
- Replace the placeholder weight paths in `advanced_quantum_optimizer.py` and `enhanced_quantum_walk.py`
- Compute and return `factor_exposures` in the optimize API response
- Add factor-constrained optimization: max exposure to any single factor

**Out of scope:**
- External Barra / FactSet / MSCI factor database integration (requires paid data)
- Fama-French 5-factor (requires external factor return series download)
- Machine learning factor discovery
- Factor backtesting (parking lot)

---

## Affected Files

| File | Change |
|------|--------|
| `services/factor_models.py` | New file — factor loading computation |
| `core/quantum_inspired/advanced_quantum_optimizer.py` | Replace placeholder weight paths at lines 589, 867 |
| `core/quantum_inspired/enhanced_quantum_walk.py` | Replace placeholder at line 364 |
| `core/portfolio_optimizer.py` | Add factor exposure to response payload |
| `api/app.py` | Include `factor_exposures` in optimize response |

---

## Factor Definitions (return-based proxies)

All four factors are computed from the asset universe itself — no external data required.

| Factor | Proxy | How computed |
|--------|-------|-------------|
| **Market (β)** | Universe equal-weight return | OLS β of each asset vs equal-weight portfolio |
| **Size** | Market cap proxy = inverse of 1-year realized volatility | Rank assets by vol; small = high vol (crude but signal-rich) |
| **Momentum** | 12-month return minus most recent 1 month | Rank and z-score |
| **Low-Vol** | Negative of 6-month realized volatility | Rank and z-score |

Factor score matrix `F` is `(n_assets × 4)`, z-scored across assets.

---

## Factor Loading Computation

```python
# services/factor_models.py

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

def compute_factor_scores(returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a (n_assets, 4) DataFrame of factor scores.
    Factors: market_beta, size_score, momentum_score, low_vol_score.
    All scores are z-scored across assets (mean=0, std=1).
    """
    # Market beta
    mkt = returns_df.mean(axis=1)
    betas = {}
    for col in returns_df.columns:
        model = LinearRegression().fit(mkt.values.reshape(-1, 1), returns_df[col].values)
        betas[col] = model.coef_[0]

    # Size (inverse vol proxy)
    vols = returns_df.std()
    size = -vols  # lower vol = "larger" in this proxy

    # Momentum (12m - 1m)
    mom = returns_df.iloc[-252:].mean() - returns_df.iloc[-21:].mean()

    # Low-vol
    low_vol = -returns_df.iloc[-126:].std()

    factors = pd.DataFrame({
        'market_beta': pd.Series(betas),
        'size': size,
        'momentum': mom,
        'low_vol': low_vol,
    })

    # Z-score each factor across assets
    return (factors - factors.mean()) / (factors.std() + 1e-8)


def compute_portfolio_factor_exposure(weights: np.ndarray, factor_scores: pd.DataFrame) -> dict:
    """Weighted average factor exposure of the portfolio."""
    exposure = factor_scores.T @ weights
    return {
        'market_beta': float(exposure['market_beta']),
        'size': float(exposure['size']),
        'momentum': float(exposure['momentum']),
        'low_vol': float(exposure['low_vol']),
    }
```

---

## Implementation Plan

1. **Create `services/factor_models.py`** with `compute_factor_scores()` and `compute_portfolio_factor_exposure()` as above.

2. **Replace placeholder at `advanced_quantum_optimizer.py` line 589**:
   - Call `compute_factor_scores(returns_df)` to get factor score matrix
   - Use factor scores to tilt initial weights toward high-momentum, low-beta assets as a starting point before quantum optimization

3. **Replace placeholder at `advanced_quantum_optimizer.py` line 867**:
   - Compute actual diversification ratio: `(Σ w_i σ_i) / σ_p`
   - Replace hardcoded `0.75`

4. **Replace placeholder at `enhanced_quantum_walk.py` line 364**:
   - Use factor scores as transition weights in the quantum walk graph — assets with higher momentum score get higher walk probability

5. **Add factor exposures to optimize response** in `core/portfolio_optimizer.py`:
   ```python
   "factor_exposures": compute_portfolio_factor_exposure(weights, factor_scores)
   ```

6. **Add factor constraint support** — optional `max_factor_exposure` dict in request:
   ```json
   { "max_factor_exposure": { "market_beta": 1.2, "momentum": 0.5 } }
   ```
   Post-optimization, if any exposure exceeds the limit, apply a penalized re-solve.

7. **Write tests**:
   - `test_factor_scores_shape` — output is `(n_assets, 4)`, all z-scored (mean ≈ 0)
   - `test_portfolio_factor_exposure_range` — values in reasonable range (e.g., beta in [-2, 3])
   - `test_diversification_ratio_not_placeholder` — returned value is computed, not 0.75

---

## Acceptance Criteria

- [ ] `POST /api/portfolio/optimize` response includes `factor_exposures` block with four factor values
- [ ] No `# Placeholder` comments remain in `advanced_quantum_optimizer.py` or `enhanced_quantum_walk.py`
- [ ] `diversification_ratio` is computed from actual weights and covariance, not hardcoded
- [ ] All three new tests pass
- [ ] Factor computation adds < 200ms to optimize latency (profile if needed)

---

## Parking Lot

- External Fama-French 3/5 factor series via Ken French data library (requires download)
- Barra-style factor risk model (requires licensed data)
- Factor alpha decomposition: how much return comes from each factor vs alpha
- Factor timing: switch between factor tilts based on macro regime (see `09-regime-detection.md`)
