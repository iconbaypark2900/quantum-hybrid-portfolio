# 03 — Server-Side Persistent Run History

**Priority:** High  
**Status:** Partial — frontend run history page exists (`web/src/app/(ledger)/reports/runs/[id]/page.tsx`) but there is no backend persistence layer storing run results by ID  
**Area:** Backend `api/app.py`, `services/`, DB schema; Frontend `web/src/`

---

## Problem

Optimization run results currently live only in the browser's `localStorage` via `LedgerSessionContext`. When the user closes the browser, refreshes, or opens a different machine, all run history is lost.

The Next.js app has routes for `/reports/runs/[id]` and `/reports/history/[id]` — these imply a server-side ID exists — but the Flask API has no `GET /api/runs/{id}` endpoint and does not persist run records to the database.

Consequences:
- No reproducibility: you cannot re-run or audit a past optimization
- No cross-device access: results are not shareable by URL
- No turn-over constraint tracking (cannot compare weights to a prior allocation)
- No compliance audit trail

---

## Scope

**In scope:**
- Add a `run_history` table to the SQLite/PostgreSQL DB schema
- On every `POST /api/portfolio/optimize` call, persist inputs + outputs as a run record and return `run_id` in the response
- Add `GET /api/runs` (paginated list) and `GET /api/runs/{run_id}` (full record) endpoints
- Wire the Next.js `/reports/runs/[id]` page to fetch from the API
- Wire the `/reports/history/[id]` page to the same source

**Out of scope:**
- Run comparison diffing UI (parking lot)
- Turn-over-constrained re-optimization using prior run (depends on this; add after)
- Backtest run history (separate table, similar pattern)

---

## Affected Files

| File | Change |
|------|--------|
| `api/app.py` | Add run persistence on optimize, add `GET /api/runs` and `GET /api/runs/{id}` |
| `services/` | Add `run_repository.py` — DB read/write for run records |
| DB schema | Add `optimization_runs` table |
| `web/src/app/(ledger)/reports/runs/[id]/page.tsx` | Fetch from `GET /api/runs/{id}` instead of session state |
| `web/src/app/(ledger)/reports/history/[id]/page.tsx` | Same |
| `web/src/lib/api.ts` | Add `fetchRun(id)` and `listRuns()` API calls |

---

## DB Schema

```sql
CREATE TABLE IF NOT EXISTS optimization_runs (
    id          TEXT PRIMARY KEY,           -- UUID
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT NOT NULL,              -- ISO 8601
    objective   TEXT NOT NULL,
    tickers     TEXT NOT NULL,              -- JSON array
    constraints TEXT NOT NULL,             -- JSON object
    inputs      TEXT NOT NULL,             -- full request payload (JSON)
    outputs     TEXT NOT NULL,             -- full response payload (JSON)
    backend     TEXT,                      -- 'simulator' | 'ibm_hardware' | 'braket_mock' etc.
    duration_ms INTEGER,
    status      TEXT NOT NULL DEFAULT 'success'  -- 'success' | 'error'
);
CREATE INDEX IF NOT EXISTS idx_runs_tenant_created ON optimization_runs(tenant_id, created_at DESC);
```

---

## Implementation Plan

1. **Create `services/run_repository.py`**:
   ```python
   def save_run(db, run_id, tenant_id, objective, tickers, constraints, inputs, outputs, backend, duration_ms, status): ...
   def get_run(db, run_id, tenant_id): ...
   def list_runs(db, tenant_id, limit=50, offset=0): ...
   ```

2. **Apply migration** — add the table creation SQL to the DB init path in `api/app.py` (alongside existing table creation calls).

3. **Wrap the optimize endpoint** — after a successful optimization, call `save_run(...)` and append `run_id` to the response:
   ```json
   { "run_id": "uuid-...", "sharpe_ratio": 1.42, ... }
   ```
   This must not slow the response — use `try/except` around persistence so a DB failure does not break optimization.

4. **Add `GET /api/runs` endpoint**:
   - Query param: `limit` (default 50), `offset` (default 0), `tenant_id` (from auth header)
   - Returns: `{ runs: [{id, created_at, objective, tickers, sharpe_ratio, status}], total }`

5. **Add `GET /api/runs/{run_id}` endpoint**:
   - Returns full `inputs` + `outputs` JSON blobs
   - Returns 404 if `run_id` not found for this tenant

6. **Update `web/src/lib/api.ts`** — add:
   ```typescript
   export async function listRuns(limit = 50, offset = 0): Promise<RunListResponse>
   export async function fetchRun(id: string): Promise<RunDetail>
   ```

7. **Update `/reports/runs/[id]/page.tsx`** — on mount, call `fetchRun(id)` from API; fall back to `localStorage` session if API returns 404 (backward compat for pre-existing sessions).

8. **Update `/reports/history/[id]/page.tsx`** — same pattern.

9. **Write tests**:
   - `test_run_saved_on_optimize` — after `POST /api/portfolio/optimize`, `GET /api/runs/{id}` returns status 200
   - `test_run_list_pagination` — second page returns different records
   - `test_run_tenant_isolation` — run saved under tenant A is not visible to tenant B

---

## Acceptance Criteria

- [ ] Every successful `POST /api/portfolio/optimize` response includes `run_id`
- [ ] `GET /api/runs` returns the list of past runs (most recent first)
- [ ] `GET /api/runs/{id}` returns full inputs and outputs
- [ ] `/reports/runs/[id]` page fetches from the API and renders the result
- [ ] A DB failure during persistence does not break the optimize response (degrades gracefully)
- [ ] All three new tests pass

---

## Parking Lot

- Run-to-run diff view in UI: compare weights / metrics of two runs side by side
- Backtest run history (same table pattern, different endpoint)
- Turn-over constraint: diff weights from `run_id` vs new allocation
- Soft-delete / archive runs (admin endpoint)
