# 01 — Empirical VaR & Correlation Matrix

**Priority:** High  
**Status:** Placeholder in production code  
**Area:** Backend — `api/app.py`, `services/`

---

## Problem

In `api/app.py` around line 934, the scenario simulation path builds a covariance/correlation matrix for VaR using a hardcoded `0.3` for every off-diagonal entry:

```python
row.append(0.3)  # Placeholder correlation
```

This means:

- Every stress scenario VaR calculation assumes a uniform 30% pairwise correlation between all assets regardless of their actual historical relationship.
- A tech-heavy portfolio and a bond-heavy portfolio would show the same correlation structure.
- The VaR number returned to the frontend is structurally wrong for any real portfolio.

Additionally, the `risk_metrics` returned from optimization and the `risk_metrics` used in scenario simulation are computed from separate code paths using different covariance assumptions. They should be derived from the same empirical matrix.

---

## Scope

**In scope:**
- Replace the placeholder `0.3` correlation with the empirical correlation matrix computed from the same price returns used for optimization
- Ensure the scenario simulation VaR and the optimization VaR use the same covariance source
- Add CVaR (conditional value at risk at 95%) as a returned metric alongside VaR
- Add historical simulation VaR as an alternative to parametric (normal-assumption) VaR

**Out of scope:**
- Portfolio stress testing UI redesign (that is a separate frontend task)
- Monte Carlo simulation path (future enhancement)
- Factor-model-adjusted covariance (covered in `08-factor-models.md`)

---

## Affected Files

| File | Location | Issue |
|------|----------|-------|
| `api/app.py` | ~line 934 | `row.append(0.3)` — hardcoded placeholder correlation |
| `api/app.py` | ~line 616 | `generate_mock_data()` mixed into production module |
| `services/risk_models.py` | Entire file | Should be the single source of truth for correlation/covariance; confirm it is actually called from both optimization and simulation paths |
| `core/portfolio_optimizer.py` | Covariance section | Confirm it returns the covariance matrix in the result payload for downstream reuse |

---

## Implementation Plan

1. **Verify `services/risk_models.py`** — confirm it has a `compute_covariance(returns_df)` and `compute_correlation(returns_df)` function. If not, add them.

2. **Refactor scenario simulation covariance path in `api/app.py`**:
   - After fetching price data, compute empirical returns
   - Call `services/risk_models.compute_correlation(returns_df)` instead of building the fake matrix
   - Fall back to a diagonal identity only if fewer than 2 periods of data exist (log a warning)

3. **Add CVaR computation** in `services/risk_models.py`:
   ```python
   def compute_cvar(weights, returns_df, alpha=0.05):
       portfolio_returns = returns_df @ weights
       var = portfolio_returns.quantile(alpha)
       cvar = portfolio_returns[portfolio_returns <= var].mean()
       return float(cvar)
   ```

4. **Add historical simulation VaR** alongside parametric VaR:
   ```python
   def compute_var_historical(weights, returns_df, alpha=0.05):
       portfolio_returns = returns_df @ weights
       return float(portfolio_returns.quantile(alpha))
   ```

5. **Return both VaR types and CVaR** in the `risk_metrics` block of the optimize response:
   ```json
   {
     "risk_metrics": {
       "var_95_parametric": 0.021,
       "var_95_historical": 0.019,
       "cvar_95": 0.031,
       "correlation_source": "empirical"
     }
   }
   ```

6. **Remove `generate_mock_data()`** from `api/app.py` or gate it behind a `?mock=true` query param that is only active when `FLASK_ENV=development`.

7. **Write tests** in `tests/test_services.py`:
   - `test_compute_correlation_shape` — confirm output is `(n, n)` symmetric matrix
   - `test_var_historical_vs_parametric` — both should be within 10% of each other on normally distributed returns
   - `test_cvar_exceeds_var` — CVaR must always be >= VaR (absolute magnitude)

---

## Acceptance Criteria

- [ ] Calling `POST /api/portfolio/optimize` with real tickers returns `risk_metrics.correlation_source = "empirical"`, not `"placeholder"`
- [ ] Scenario simulation VaR no longer uses a uniform 0.3 correlation matrix
- [ ] `risk_metrics` includes `var_95_parametric`, `var_95_historical`, and `cvar_95`
- [ ] `test_compute_correlation_shape` passes
- [ ] `test_cvar_exceeds_var` passes
- [ ] `generate_mock_data` is not callable in a `FLASK_ENV=production` context

---

## Parking Lot

- Monte Carlo VaR (10k path simulation) — adds compute cost, defer
- Factor-adjusted covariance (Ledoit-Wolf shrinkage or Barra-style) — see `08-factor-models.md`
- Stress correlation matrices (e.g., 2008 crisis correlation regime) — useful for scenario testing, defer
