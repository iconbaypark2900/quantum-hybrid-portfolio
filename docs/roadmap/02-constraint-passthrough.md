# 02 — Constraint Pass-Through in All Optimizer Methods

**Priority:** High  
**Status:** Broken — 4 tests explicitly skipped with note "Constraints not supported in notebook-methods thin wrapper"  
**Area:** Backend — `methods/`, `core/optimizers/`, `tests/test_services.py`

---

## Problem

The `methods/` directory contains thin wrappers (`vqe.py`, `qaoa.py`, `qubo_sa.py`, `hybrid_pipeline.py`, `markowitz.py`, `hrp.py`, `equal_weight.py`) that are the public interface for each optimizer. Currently they do not uniformly forward constraint arguments (`weight_min`, `weight_max`, sector limits, `k_select`, `k_screen`) to the underlying optimizer implementations.

This means:

- A user who sets weight bounds of `[0.02, 0.15]` in the portfolio lab may or may not get those constraints applied depending on which objective they choose.
- The failure is silent — the optimizer returns results without indicating that constraints were dropped.
- Four tests in `tests/test_services.py` are skipped rather than fixed, confirming this is a known regression.

---

## Scope

**In scope:**
- Audit every `methods/*.py` wrapper to confirm it accepts and passes `weight_min`, `weight_max`, `k_select`, `k_screen`, and `sector_constraints`
- Fix any wrapper that drops or ignores these arguments
- Add a `constraint_violations` field to optimize responses indicating which constraints were binding
- Un-skip the 4 skipped tests and make them pass

**Out of scope:**
- Adding new constraint types (e.g., ESG screens, factor exposure limits) — those are separate features
- Frontend constraint editor redesign

---

## Affected Files

| File | Issue |
|------|-------|
| `methods/vqe.py` | Verify `weight_min` / `weight_max` forwarded to `core/optimizers/vqe.py` |
| `methods/qaoa.py` | Verify same |
| `methods/qubo_sa.py` | Verify `k_select` forwarded to QUBO formulation |
| `methods/hybrid_pipeline.py` | Verify all constraints forwarded through the hybrid chain |
| `methods/markowitz.py` | Verify scipy bounds include `weight_min` / `weight_max` |
| `methods/hrp.py` | HRP does not naturally enforce weight bounds — needs post-processing clip + renorm |
| `methods/equal_weight.py` | Equal-weight ignores `k_select` — should apply cardinality if set |
| `tests/test_services.py` | 4 skipped tests — restore and fix |
| `core/portfolio_optimizer.py` | Constraint forwarding from orchestrator to method |

---

## Implementation Plan

1. **Audit each `methods/*.py` wrapper** — for each file confirm the function signature includes:
   ```python
   def optimize(tickers, returns, cov, weight_min=0.0, weight_max=1.0,
                k_select=None, k_screen=None, sector_constraints=None, **kwargs):
   ```

2. **Fix `methods/hrp.py`** — HRP produces unconstrained weights; after optimization apply:
   ```python
   weights = np.clip(weights, weight_min, weight_max)
   weights /= weights.sum()
   ```
   Log a warning if clipping changed the sum by more than 5%.

3. **Fix `methods/equal_weight.py`** — if `k_select` is set, select top-`k` by Sharpe or equal randomly, then equal-weight only those:
   ```python
   if k_select and k_select < len(tickers):
       # select k_select assets, zero out the rest
   ```

4. **Add `constraint_report` to optimizer return dict** in `core/portfolio_optimizer.py`:
   ```python
   "constraint_report": {
       "weight_min_applied": weight_min,
       "weight_max_applied": weight_max,
       "n_clipped_min": int((weights < weight_min + 1e-6).sum()),
       "n_clipped_max": int((weights > weight_max - 1e-6).sum()),
       "k_select": k_select,
   }
   ```

5. **Un-skip the 4 tests in `tests/test_services.py`** — update them to assert:
   - All returned weights satisfy `weight_min <= w <= weight_max`
   - If `k_select=5` is passed, at most 5 non-zero weights are returned
   - `constraint_report` is present in the response

6. **Add integration test** in `tests/test_api_integration.py`:
   - `POST /api/portfolio/optimize` with `weight_min=0.05, weight_max=0.20, k_select=5`
   - Assert all returned weights in `[0.05, 0.20]` and at most 5 are non-zero

---

## Acceptance Criteria

- [ ] All 4 previously skipped constraint tests pass
- [ ] New integration test for constraint enforcement passes for all objectives (`markowitz`, `hrp`, `vqe`, `qaoa`, `qubo_sa`, `hybrid`)
- [ ] Every `methods/*.py` wrapper signature includes `weight_min`, `weight_max`, `k_select`
- [ ] API response includes `constraint_report` block
- [ ] No constraint is silently dropped — if an objective cannot honor a constraint, it returns a 400 with a clear message

---

## Parking Lot

- Sector exposure limits (`max_sector_weight`) — requires sector metadata from market data; defer to factor model spec
- ESG / exclusion screens — separate compliance feature
- Turn-over constraints (max weight change vs previous allocation) — needs run history first (see `03-persistent-run-history.md`)
