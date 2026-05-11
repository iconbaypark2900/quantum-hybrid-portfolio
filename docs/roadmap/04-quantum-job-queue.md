# 04 — Async Quantum Job Queue & Live Status Polling

**Priority:** High  
**Status:** Partial — IBM Quantum jobs submit and return a job ID, but results are lost if the browser closes; no background polling or notification  
**Area:** Backend `api/app.py`, `services/ibm_quantum.py`; Frontend `web/src/app/(ledger)/quantum/`

---

## Problem

IBM Quantum and Braket jobs are long-running (minutes to hours on real hardware). The current architecture:

1. Submits a job to the IBM Runtime
2. Returns the job ID immediately
3. The frontend must keep the browser open and poll manually

If the user closes the browser tab, the job result is permanently lost from the UI. There is no background worker that picks up the result when it completes, no persistence of the result in the DB, and no mechanism to notify the user when a job finishes.

Additionally, the Quantum Engine page shows job status as a one-shot snapshot — it does not live-refresh.

---

## Scope

**In scope:**
- Persist submitted quantum jobs (job ID, backend, status, submission params) to the DB
- Background polling loop (Flask APScheduler or a simple DB-backed polling approach) that checks pending job status and writes results when complete
- `GET /api/jobs` — list jobs (pending/running/done/error) for the current tenant
- `GET /api/jobs/{id}` — full job status and result payload when complete
- `GET /api/jobs/{id}/stream` — Server-Sent Events endpoint so the frontend can subscribe to live status without WebSockets
- Frontend Quantum Engine page: "My Jobs" panel that fetches from `GET /api/jobs` and auto-refreshes

**Out of scope:**
- Full WebSocket infrastructure (SSE is sufficient and simpler for Flask)
- Celery / Redis queue (APScheduler or a cron-style background thread avoids infrastructure dependency)
- Braket async polling (same pattern, defer to `14-hardware-integration.md`)

---

## Affected Files

| File | Change |
|------|--------|
| `api/app.py` | Add `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/stream`; persist job on submission; start background poller at app startup |
| `services/ibm_quantum.py` | Add `get_job_status(job_id)` and `retrieve_job_result(job_id)` if not already present |
| DB schema | Add `quantum_jobs` table |
| `web/src/app/(ledger)/quantum/page.tsx` | Add "My Jobs" panel with live-refresh |
| `web/src/lib/api.ts` | Add `listJobs()`, `fetchJob(id)`, streaming hook |

---

## DB Schema

```sql
CREATE TABLE IF NOT EXISTS quantum_jobs (
    id              TEXT PRIMARY KEY,         -- UUID internal key
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    provider        TEXT NOT NULL,            -- 'ibm' | 'braket'
    backend_job_id  TEXT NOT NULL,            -- ID returned by IBM/Braket
    backend_name    TEXT,                     -- e.g. 'ibmq_qasm_simulator'
    objective       TEXT,
    tickers         TEXT,                     -- JSON
    submitted_at    TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | running | done | error
    result          TEXT,                     -- JSON blob when done
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS idx_qjobs_tenant_status ON quantum_jobs(tenant_id, status);
```

---

## Implementation Plan

1. **Add `quantum_jobs` table** to DB init in `api/app.py`.

2. **Persist job on submission** — after calling IBM Runtime `session.run(...)`, insert a row into `quantum_jobs` with `status='pending'`.

3. **Create background poller** — on app startup, start a background thread (or use APScheduler with `BackgroundScheduler`):
   ```python
   def poll_pending_jobs():
       pending = db.query("SELECT * FROM quantum_jobs WHERE status IN ('pending','running')")
       for job in pending:
           status = ibm_quantum.get_job_status(job.backend_job_id)
           if status == 'DONE':
               result = ibm_quantum.retrieve_job_result(job.backend_job_id)
               db.update(job.id, status='done', result=json.dumps(result), completed_at=now())
           elif status == 'ERROR':
               db.update(job.id, status='error', error_message=..., completed_at=now())
   ```
   Run every 30 seconds. Gate with `IBM_QUANTUM_TOKEN` present to avoid polling without credentials.

4. **Add `GET /api/jobs`** — returns `[{id, backend_job_id, status, objective, tickers, submitted_at, completed_at}]`, paginated.

5. **Add `GET /api/jobs/{id}`** — returns full record including `result` when done.

6. **Add `GET /api/jobs/{id}/stream`** (SSE):
   ```python
   def event_stream(job_id):
       while True:
           job = db.get_job(job_id)
           yield f"data: {json.dumps({'status': job.status})}\n\n"
           if job.status in ('done', 'error'):
               break
           time.sleep(5)
   ```

7. **Frontend — "My Jobs" panel** in `web/src/app/(ledger)/quantum/page.tsx`:
   - On mount, call `listJobs()` and poll every 15 seconds
   - Show status badge (Pending / Running / Done / Error) with color
   - When a job transitions to Done, show Sharpe / weights summary inline
   - Link to `/reports/runs/{id}` when result is available

8. **Write tests**:
   - `test_job_persisted_on_submit` — after submitting, `GET /api/jobs` returns the job
   - `test_job_status_update` — mock IBM status response → assert DB row updated
   - `test_job_stream_terminates` — SSE stream closes when job reaches terminal state

---

## Acceptance Criteria

- [ ] Submitting an IBM optimization job returns a `job_id` that persists in the DB across browser restarts
- [ ] `GET /api/jobs` lists all jobs for the current tenant
- [ ] Background poller updates job status without any browser interaction
- [ ] Frontend "My Jobs" panel shows live status and auto-refreshes
- [ ] SSE stream closes cleanly when job enters `done` or `error` state
- [ ] All three new tests pass

---

## Parking Lot

- Braket job polling (same pattern, add `provider='braket'` path)
- Push notification (email/webhook on job completion) — needs notification service
- Job cancellation endpoint: `DELETE /api/jobs/{id}`
- Max concurrent jobs limit per tenant
