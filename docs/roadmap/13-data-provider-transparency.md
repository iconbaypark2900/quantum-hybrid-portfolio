# 13 — Data Provider Transparency in UI

**Priority:** Medium  
**Status:** Hardcoded strings — Dashboard shows "Market Data: Connected" regardless of actual provider or fallback state  
**Area:** Backend `api/app.py`, `services/data_provider_v2.py`; Frontend Dashboard, Portfolio Lab

---

## Problem

The system dashboard in `web/src/app/(ledger)/dashboard/page.tsx` shows four hardcoded system status cards:

```typescript
{ label: "Market Data", value: "Connected", color: "text-ql-tertiary", ... }
{ label: "Quantum Engine", value: "Simulator", color: "text-ql-primary", ... }
```

These strings are **always** "Connected" and "Simulator" regardless of what actually happened:

- If Tiingo is rate-limited and the system fell back to yfinance (deprecated), the UI shows "Connected"
- If the data is 3 days stale (cached), the UI shows "Connected"
- If the quantum backend is actually IBM hardware (not simulator), the UI shows "Simulator"

Additionally, the optimize response does not include `data_source`, `data_timestamp`, or `fallback_used` fields, so even if the UI wanted to show the real state, the data is not available.

---

## Scope

**In scope:**
- Add `data_source`, `data_timestamp`, `fallback_used`, `data_staleness_hours` to all optimize and backtest API responses
- Add `quantum_backend_mode` (`simulator` | `hardware` | `mock`) to optimize responses using IBM/Braket objectives
- Update Dashboard system status cards to use live data from the health endpoint or last optimize response
- Show a stale data warning banner when data is older than 24 hours
- Show a fallback warning when yfinance was used instead of Tiingo

**Out of scope:**
- Real-time tick price streaming
- Data quality scoring or return anomaly detection
- Alternative data sources (sentiment, macro — parking lot)

---

## Affected Files

| File | Change |
|------|--------|
| `services/data_provider_v2.py` | Return `data_source`, `timestamp`, `fallback_used` in fetch result |
| `api/app.py` | Include data provenance in optimize/backtest responses |
| `api/app.py` | Update `/api/health` to include market data status and current provider |
| `web/src/app/(ledger)/dashboard/page.tsx` | Replace hardcoded status cards with live data |
| `web/src/app/(ledger)/portfolio/page.tsx` | Show data provenance banner below KPIs |

---

## Backend Changes

### Data Provider Response Shape

Update `services/data_provider_v2.py` fetch functions to return a provenance envelope:

```python
@dataclass
class MarketDataResult:
    prices: pd.DataFrame
    returns: pd.DataFrame
    covariance: pd.DataFrame
    data_source: str           # 'tiingo' | 'yfinance' | 'alpaca' | 'polygon'
    fallback_used: bool        # True if primary provider failed and fallback was used
    timestamp: str             # ISO 8601 of when data was fetched
    earliest_date: str
    latest_date: str
    missing_tickers: list[str] # tickers requested but not found
```

### Optimize Response Addition

```json
{
  "weights": { ... },
  "sharpe_ratio": 1.42,
  "data_provenance": {
    "data_source": "tiingo",
    "fallback_used": false,
    "data_timestamp": "2026-04-16T08:00:00Z",
    "data_staleness_hours": 2.1,
    "missing_tickers": [],
    "earliest_date": "2023-01-03",
    "latest_date": "2026-04-15"
  },
  "quantum_backend": {
    "mode": "simulator",
    "backend_name": "statevector_simulator",
    "ibm_runtime_used": false
  }
}
```

### Health Endpoint Addition

Add to `GET /api/health` response:

```json
{
  "status": "healthy",
  "dependencies": {
    "market_data": {
      "provider": "tiingo",
      "status": "ok",
      "last_fetch": "2026-04-16T08:00:00Z"
    },
    "quantum": {
      "ibm_connected": true,
      "braket_enabled": false,
      "mode": "simulator"
    }
  }
}
```

---

## Frontend Changes

### Dashboard — Replace Hardcoded Status Cards

Replace the static `SystemStatusCard` data with values from the health endpoint and last optimize result:

```typescript
// Fetch real status from /api/health
const { data: health } = useHealthCheck();

const systemStatus = [
  {
    label: "API",
    value: health?.status === "healthy" ? "Online" : "Offline",
    color: health?.status === "healthy" ? "text-ql-tertiary" : "text-ql-error",
    desc: "Flask backend",
  },
  {
    label: "Market Data",
    value: health?.dependencies?.market_data?.provider ?? "Unknown",
    color: health?.dependencies?.market_data?.status === "ok" ? "text-ql-tertiary" : "text-ql-error",
    desc: `Provider: ${health?.dependencies?.market_data?.provider}`,
  },
  {
    label: "Quantum Engine",
    value: health?.dependencies?.quantum?.mode ?? "Unknown",
    color: health?.dependencies?.quantum?.ibm_connected ? "text-ql-tertiary" : "text-ql-primary",
    desc: "IBM Runtime or local simulator",
  },
];
```

### Stale Data Warning Banner

In `web/src/app/(ledger)/portfolio/page.tsx`, after optimization:

```tsx
{result?.data_provenance?.data_staleness_hours > 24 && (
  <div className="bg-ql-error/10 border border-ql-error/30 rounded-lg px-4 py-3 text-xs text-ql-error">
    ⚠️ Market data is {result.data_provenance.data_staleness_hours.toFixed(0)} hours old.
    Prices may not reflect current market conditions.
  </div>
)}

{result?.data_provenance?.fallback_used && (
  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-xs text-amber-700">
    ⚠️ Primary data provider (Tiingo) was unavailable. Results use yfinance fallback data.
    Verify data quality before making allocation decisions.
  </div>
)}
```

---

## Implementation Plan

1. **Update `services/data_provider_v2.py`** — make fetch functions return `MarketDataResult` dataclass instead of bare DataFrames. Pass `fallback_used=True` when the fallback path activates.

2. **Propagate provenance** through `services/market_data.py` → `core/portfolio_optimizer.py` → `api/app.py` optimize handler → response body.

3. **Update `/api/health`** to query the market data provider and return live status.

4. **Update Dashboard status cards** to read from health endpoint instead of hardcoded strings.

5. **Add warning banners** to Portfolio Lab page.

6. **Write tests**:
   - `test_optimize_response_includes_data_provenance` — assert `data_provenance` keys present
   - `test_fallback_used_flag_set` — when Tiingo fails, `fallback_used=True`
   - `test_health_endpoint_includes_market_data_status`

---

## Acceptance Criteria

- [ ] `POST /api/portfolio/optimize` response includes `data_provenance` block
- [ ] Dashboard system status cards show real provider name and mode, not hardcoded strings
- [ ] Stale data warning appears when data is > 24 hours old
- [ ] Fallback warning appears when yfinance was used
- [ ] `/api/health` includes `dependencies.market_data.provider` and `dependencies.quantum.mode`
- [ ] All three new tests pass

---

## Parking Lot

- Data quality score: flag suspicious returns (> 5 sigma) before optimization
- Missing ticker alert: show which requested tickers had no data and were dropped
- Alternative data panel: sentiment index, macro indicators as overlay
- Provider SLA tracking: log fallback frequency over time
