# 05 — Portfolio Time-Series Charting

**Priority:** High  
**Status:** Missing — backend backtest endpoints exist and return equity curves; frontend renders only a holdings list and bar widths, no charts  
**Area:** Frontend `web/src/`, potentially a new shared charting component

---

## Problem

The platform runs backtests and returns equity curves (`equity_curve`, `cumulative_returns`, drawdown series) from the Flask API. The frontend never renders these as charts. Users see:

- A sorted holdings list with proportional bar widths
- A sector allocation breakdown as a text list
- KPI cards (Sharpe, return, volatility, VaR)

What is absent:
- Time-series equity curve vs benchmark
- Rolling Sharpe / rolling volatility over the backtest window
- Drawdown chart with max drawdown labeled
- Efficient frontier scatter (risk vs return across objectives)

Without charts, the platform cannot demonstrate the core proposition — "quantum-enhanced returns outperform classical" — in a visually compelling or analytically credible way.

---

## Scope

**In scope:**
- Add an `EquityCurveChart` component using Recharts (already a likely dependency; if not, add it)
- Add a `DrawdownChart` component
- Add an `EfficientFrontierChart` component for the Simulations page
- Wire `/portfolio` page to request a backtest result alongside optimization and render the equity curve
- Wire `/simulations` page to replace heuristic stress cards with backend-computed scenario impacts

**Out of scope:**
- Real-time tick data streaming (websocket price feed)
- Interactive weight editor with chart re-computation on drag
- 3D risk surface visualization

---

## Affected Files

| File | Change |
|------|--------|
| `web/src/components/` | Add `EquityCurveChart.tsx`, `DrawdownChart.tsx`, `EfficientFrontierChart.tsx` |
| `web/src/app/(ledger)/portfolio/page.tsx` | After optimize, also call backtest endpoint and render charts below KPIs |
| `web/src/app/(ledger)/simulations/page.tsx` | Replace `heuristicImpact()` with backend scenario comparison results |
| `web/src/lib/api.ts` | Add `runBacktest(params)` call if not present |
| `package.json` in `web/` | Add `recharts` if not already listed |

---

## Component Specs

### `EquityCurveChart`

```typescript
interface EquityCurveChartProps {
  dates: string[];          // ISO date strings
  portfolioValues: number[]; // cumulative return multiplier (1.0 = start)
  benchmarkValues?: number[]; // optional benchmark
  title?: string;
}
```

- X-axis: dates (monthly label)
- Y-axis: cumulative return (%)
- Two lines: portfolio (ql-primary color) and optional benchmark (ql-outline color)
- Hover tooltip showing date, portfolio value, benchmark value, spread

### `DrawdownChart`

```typescript
interface DrawdownChartProps {
  dates: string[];
  drawdowns: number[]; // negative fractions, e.g. -0.12 = -12%
}
```

- X-axis: dates
- Y-axis: drawdown % (0 to -N%)
- Area fill in `ql-error` color below the zero line
- Annotation: max drawdown value and date

### `EfficientFrontierChart`

```typescript
interface EfficientFrontierPoint {
  objective: string;
  volatility: number;
  expected_return: number;
  sharpe: number;
}
interface EfficientFrontierChartProps {
  points: EfficientFrontierPoint[];
}
```

- Scatter plot: X = volatility, Y = expected return
- Each point labeled by objective name
- Color-coded by Sharpe ratio (gradient)
- Capital Market Line if a risk-free rate is provided

---

## Implementation Plan

1. **Check `web/package.json` for `recharts`** — add if missing:
   ```bash
   cd web && npm install recharts
   ```

2. **Create `web/src/components/EquityCurveChart.tsx`** — Recharts `LineChart` with `ResponsiveContainer`.

3. **Create `web/src/components/DrawdownChart.tsx`** — Recharts `AreaChart` with negative-fill styling.

4. **Create `web/src/components/EfficientFrontierChart.tsx`** — Recharts `ScatterChart`.

5. **Update `web/src/app/(ledger)/portfolio/page.tsx`**:
   - After optimization completes, call `runBacktest({ tickers, weights, start_date, end_date })`
   - Render `<EquityCurveChart>` and `<DrawdownChart>` in a section below the KPI cards
   - Show a loading skeleton while backtest is in flight

6. **Update `web/src/app/(ledger)/simulations/page.tsx`**:
   - Replace `heuristicImpact()` function with backend data from `POST /api/portfolio/optimize` multi-objective comparison
   - Render `<EfficientFrontierChart>` showing all compared objectives as scatter points

7. **Confirm backtest API response shape** — the equity curve must be returned as:
   ```json
   {
     "equity_curve": {
       "dates": ["2024-01-01", ...],
       "portfolio": [1.0, 1.02, ...],
       "benchmark": [1.0, 1.01, ...]
     },
     "max_drawdown": -0.12,
     "drawdown_series": [0, -0.02, -0.12, ...]
   }
   ```
   If the backtest endpoint does not return this shape, update `services/backtest.py` to add it.

---

## Acceptance Criteria

- [ ] `/portfolio` page renders an equity curve chart after optimization + backtest completes
- [ ] `/portfolio` page renders a drawdown chart with max drawdown labeled
- [ ] `/simulations` page renders an efficient frontier scatter, not heuristic cards
- [ ] Charts use Tailwind design tokens (`ql-primary`, `ql-error`, etc.) for colors — not hardcoded hex
- [ ] Charts are responsive (resize correctly on mobile and narrow panels)
- [ ] Recharts is listed in `web/package.json` dependencies
- [ ] If backtest data is unavailable, charts show an empty state, not an error crash

---

## Parking Lot

- Rolling Sharpe / rolling volatility chart (requires window parameter in backtest)
- Interactive weight drag-to-reoptimize
- 3D risk surface (volatility × return × correlation) — computationally expensive, deferred
- Benchmark selection dropdown (SPY, QQQ, custom ticker)
