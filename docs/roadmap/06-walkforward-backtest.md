# 06 — Walk-Forward & Rolling-Window Backtest

**Priority:** High  
**Status:** Missing — single-period backtest exists; walk-forward, transaction costs, and turnover tracking are not implemented  
**Area:** Backend `services/backtest.py`, `api/app.py`; Frontend Simulations & Portfolio pages

---

## Problem

The current backtest runs a single historical period with a fixed allocation. This is the most optimistic possible backtest methodology because:

- The optimizer sees the full history, then the backtest "tests" it on the same data (look-ahead bias risk)
- There is no rebalancing — weights are set once and held forever
- There are no transaction costs, so all trades are assumed free
- Turnover is not tracked or reported

Walk-forward testing is the industry standard: train on period T, test on period T+1, rebalance, repeat. It produces honest out-of-sample performance estimates.

---

## Scope

**In scope:**
- Add `services/backtest.py` — `walk_forward_backtest(tickers, start, end, train_months, test_months, rebalance_freq, objective, constraints, cost_bps)` function
- Add `POST /api/backtest/walkforward` endpoint
- Transaction cost model: flat basis points on turnover
- Turnover tracking: report per-period portfolio turnover
- Return walk-forward equity curve and per-period stats
- Frontend: walk-forward results panel in Simulations page

**Out of scope:**
- Survivorship bias correction (requires historical constituent data)
- Slippage / market impact model (beyond flat bps)
- Multi-strategy tournament (compare walk-forward of 5 objectives simultaneously — parking lot)

---

## Affected Files

| File | Change |
|------|--------|
| `services/backtest.py` | Add `walk_forward_backtest()` function |
| `api/app.py` | Add `POST /api/backtest/walkforward` route |
| `web/src/lib/api.ts` | Add `runWalkForwardBacktest(params)` |
| `web/src/app/(ledger)/simulations/page.tsx` | Add walk-forward results panel |
| `web/src/components/` | Reuse `EquityCurveChart` from `05-portfolio-charting.md` |

---

## Walk-Forward Algorithm

```
periods = split(start → end, train_months, test_months, step=rebalance_freq)

prev_weights = equal_weight(n_assets)
equity = [1.0]
turnover_series = []

for (train_start, train_end, test_start, test_end) in periods:
    train_returns = fetch_returns(tickers, train_start, train_end)
    new_weights = optimize(train_returns, objective, constraints)
    
    turnover = sum(|new_weights - prev_weights|) / 2  # 0–1 range
    cost = turnover * cost_bps / 10000
    equity[-1] *= (1 - cost)  # apply cost at rebalance
    
    test_returns = fetch_returns(tickers, test_start, test_end)
    period_equity = (1 + test_returns @ new_weights).cumprod()
    equity.extend(period_equity.tolist())
    turnover_series.append(turnover)
    prev_weights = new_weights
```

---

## API Request / Response

### Request: `POST /api/backtest/walkforward`

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start": "2020-01-01",
  "end": "2024-12-31",
  "train_months": 12,
  "test_months": 3,
  "rebalance_freq": "quarterly",
  "objective": "hybrid",
  "constraints": { "weight_min": 0.02, "weight_max": 0.20 },
  "cost_bps": 10,
  "benchmark_ticker": "SPY"
}
```

### Response

```json
{
  "equity_curve": {
    "dates": ["2021-01-01", ...],
    "portfolio": [1.0, 1.04, ...],
    "benchmark": [1.0, 1.03, ...]
  },
  "summary": {
    "annualized_return": 0.142,
    "annualized_volatility": 0.18,
    "sharpe_ratio": 0.79,
    "max_drawdown": -0.21,
    "avg_turnover": 0.35,
    "total_cost_bps": 28
  },
  "periods": [
    {
      "train_start": "2020-01-01",
      "train_end": "2020-12-31",
      "test_start": "2021-01-01",
      "test_end": "2021-03-31",
      "turnover": 0.0,
      "weights": { "AAPL": 0.40, "MSFT": 0.35, "GOOGL": 0.25 },
      "period_return": 0.08
    }
  ],
  "metadata": {
    "n_periods": 16,
    "objective": "hybrid",
    "cost_bps": 10,
    "data_source": "tiingo"
  }
}
```

---

## Implementation Plan

1. **Add `walk_forward_backtest()` to `services/backtest.py`** with the algorithm above. Accept `objective` and delegate to `core/portfolio_optimizer.py` for each training period.

2. **Ensure market data fetching is cacheable** — each training period's fetch should use the same TTL cache as the standard optimize endpoint to avoid excessive API calls.

3. **Add `POST /api/backtest/walkforward`** route in `api/app.py`:
   - Validate input (start < end, train_months >= 6, etc.)
   - Run as a synchronous call for small universes (≤ 20 tickers, ≤ 5 years)
   - For larger configurations, submit as a background job and return `job_id` (reuse job queue from `04-quantum-job-queue.md`)

4. **Persist result** — use the same `run_repository.py` from `03-persistent-run-history.md` with `run_type='walkforward'`.

5. **Frontend** — add a "Walk-Forward" tab in the Simulations page:
   - Form: start, end, train months, test months, cost bps, objective selector
   - Submit → show loading state → render equity curve + summary cards when done

6. **Write tests**:
   - `test_walkforward_equity_monotone_absent_cost` — with zero costs and positive-return data, equity should trend upward
   - `test_walkforward_cost_reduces_return` — result with `cost_bps=50` should have lower final equity than `cost_bps=0`
   - `test_walkforward_turnover_range` — all turnover values must be in [0, 1]
   - `test_walkforward_period_count` — verify correct number of periods generated

---

## Acceptance Criteria

- [ ] `POST /api/backtest/walkforward` returns a valid equity curve and `periods` array
- [ ] `summary.avg_turnover` is correctly computed and in [0, 1]
- [ ] Transaction costs reduce the final equity (proven by test)
- [ ] Results are persisted and retrievable via `GET /api/runs/{id}`
- [ ] Frontend Simulations page renders the walk-forward equity curve using `EquityCurveChart`
- [ ] All four new tests pass

---

## Parking Lot

- Multi-objective tournament: run walk-forward for 5 objectives simultaneously, compare on single chart
- Survivorship bias correction
- Parametric rebalance triggers (rebalance on drift, not just calendar)
- Rolling Sharpe chart (30-day, 90-day window overlay on equity curve)
