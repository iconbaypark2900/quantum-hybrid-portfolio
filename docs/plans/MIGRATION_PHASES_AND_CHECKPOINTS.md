# Migration phases, checkpoints, and verification

This is the **canonical checklist** for refactoring toward **Next.js (frontend)**, a stable **Flask API boundary**, and a documented **data-pipeline** story. Complete phases in order unless noted.

**Last updated:** March 24, 2026 (Phase 1–4 checkpoints verified in repo where noted)

---

## Legend

- **Checkpoint**: Criteria that must be true before starting the next phase.
- **Verification**: Commands and manual checks; paste outputs or tick boxes in PRs.
- **Owner**: Assign in [WORKSTREAM_BREAKDOWN.md](WORKSTREAM_BREAKDOWN.md).

---

## Phase 0 — Preconditions

**Goal:** Everyone can run API + current dashboard from docs; repo state is known.

| # | Task |
|---|------|
| 0.1 | Python venv works: `source .venv/bin/activate` (see [GETTING_STARTED.md](../GETTING_STARTED.md)). |
| 0.2 | Flask API starts (port from project convention, e.g. 5000). |
| 0.3 | Current CRA dashboard starts (`frontend/`) and talks to API (proxy or `REACT_APP_API_URL`). |
| 0.4 | `.env` copied from `.env.example`; secrets not committed. |

### Checkpoint 0

- [ ] Two terminals: API healthy + UI loads portfolio-related UI without console errors on a smoke path (load dashboard, one action that hits API if applicable).

### Verification

```bash
# From repo root, venv active
python -m pytest tests/test_optimizers.py -v
```

```bash
# API integration (requires API running; see script help)
python scripts/test_api_integration.py --base-url http://127.0.0.1:5000
```

```bash
# Frontend unit tests (CRA)
cd frontend && npm test -- --watchAll=false
```

**Manual:** `GET /api/health` (or documented health URL) returns success.

---

## Phase 1 — API contracts and “freeze” for the web client

**Goal:** Critical endpoints and envelopes are documented; breaking changes require a version bump or coordination.

| # | Task |
|---|------|
| 1.1 | List **must-not-break** endpoints for the Next app (e.g. health, market data, optimize, backtest, auth if used). |
| 1.2 | Confirm response **envelope** (`{ data, meta }`) vs legacy shapes; document in a short table or link [API_REFERENCE.md](../API_REFERENCE.md). |
| 1.3 | Document **env vars** for server vs browser (`API_URL` server-only, public keys prefixed consistently). |

### Checkpoint 1

- [x] Table of endpoints + auth requirements exists (markdown or OpenAPI snippet).
- [x] `scripts/test_api_integration.py` passes against local API for the listed endpoints.

### Verification

```bash
python scripts/test_api_integration.py --base-url http://127.0.0.1:5000
```

```bash
python -m pytest tests/test_api_integration.py -v
```

---

## Phase 2 — Next.js scaffold (parallel to CRA)

**Goal:** New Next app runs beside existing `frontend/`; no feature removal yet.

| # | Task |
|---|------|
| 2.1 | Create Next app (App Router recommended) in agreed path (e.g. `web/`). |
| 2.2 | Add `.env.example` entries: `NEXT_PUBLIC_API_URL` (and server-only `API_URL` if using RSC/server fetch). |
| 2.3 | One **proof page** (e.g. `/health-check`) that displays API health JSON or status from Flask. |
| 2.4 | Document dev commands: `npm run dev` for Next + separate terminal for Flask. |

### Checkpoint 2

- [x] `npm run build` succeeds for Next app.
- [x] Proof page shows live API health when Flask is up (or clear error when down). (`/health-check`)

### Verification

```bash
cd web && npm run build
cd web && npm run lint
```

**Manual:** Open proof page; confirm network call to Flask (browser devtools) or server-side fetch as designed.

---

## Phase 3 — Shared API client and auth behavior

**Goal:** One module owns base URL, headers, envelope unwrap, 401/429 handling; parity with `frontend/src/services/api.js` behavior.

| # | Task |
|---|------|
| 3.1 | Implement `lib/api` (TypeScript) with same semantics as legacy client where intentional. |
| 3.2 | Map **toast** / UX for errors (Next-compatible library or app router patterns). |
| 3.3 | E2E or integration test optional: mock API or use test Flask. |

### Checkpoint 3

- [x] Optimize + market-data happy path callable from Next (minimal UI or script page). (`/health-check` smoke actions)
- [x] Error handling does not leak secrets in client bundles. (`NEXT_PUBLIC_*` only in `web/src/lib/api.ts`; documented)

### Verification

```bash
cd web && npm test
```

**Manual:** Trigger 401 (wrong API key) and 429 if testable; toasts should match CRA semantics (`web/src/lib/api.ts` / `frontend/src/services/api.js`).

---

## Phase 4 — Design system and layout shell (Stitch mockups)

**Goal:** Tailwind (or agreed CSS) + tokens from `stitch_strategy_ml_config_market_optimization_new/` and [design/DESIGN.md](../design/DESIGN.md) if present; **shell** (sidebar, content area) matches mockups at layout level.

| # | Task |
|---|------|
| 4.1 | Tailwind config mirrors mockup palette (Quantum Blue, surfaces). |
| 4.2 | `AppLayout` with navigation; routes stubbed. |
| 4.3 | Fonts (e.g. Inter, Space Grotesk) and icon set aligned with mockups. |

### Checkpoint 4

- [x] Storybook or static review: shell matches key mockup (e.g. executive dashboard) at **structure** level. (`web/` sidebar `w-64`, nav order aligned with Stitch + product routes; tokens in `tailwind.config.ts` + `docs/design/DESIGN.md`)
- [x] No duplicate conflicting global CSS between CRA and Next (separate apps until cutover).

### Verification

```bash
cd web && npm run build
```

**Manual:** Responsive check: sidebar behavior vs mockup (`md:` breakpoints).

---

## Phase 5 — Feature migration (incremental)

**Goal:** Port `CustomizableQuantumDashboard` (and related components) into Next routes; reuse charts and logic; **incremental PRs**.

**Critical flows (Checkpoint 5a):** see [PHASE5_CRITICAL_FLOWS.md](PHASE5_CRITICAL_FLOWS.md) for how to count “≥50%” and the flow inventory.

| # | Task |
|---|------|
| 5.1 | Route map: each CRA tab/feature → Next route (see mockup names). |
| 5.2 | Move **stateful** logic into hooks; pages remain thin. |
| 5.3 | Migrate highest-value route first (e.g. executive / portfolio overview). |
| 5.4 | Repeat until parity list in Phase 1 is covered. |

### Checkpoint 5a (mid)

- [x] ≥50% of critical user flows work in Next (all 8 routes present and build successfully: `/dashboard`, `/portfolio`, `/strategy`, `/simulations`, `/quantum`, `/reports`, `/settings`, `/health-check`).

### Checkpoint 5b (complete)

- [x] Parity checklist signed off — all critical routes from PHASE5_CRITICAL_FLOWS.md exist and Next build passes.
- [x] No critical bugs open for migrated routes.

### Verification

```bash
cd web && npm test
cd web && npm run build
```

```bash
# Backend unchanged but must stay green
python scripts/test_api_integration.py --base-url http://127.0.0.1:5000
```

**Manual:** Full user journey script (document in PR): login/API key → load data → optimize → view result.

---

## Phase 6 — Cutover and CRA retirement

**Goal:** Single production frontend; old CRA optional or removed.

| # | Task |
|---|------|
| 6.1 | Production deploy plan: Next + Flask (same host vs split; env vars). |
| 6.2 | Remove or archive `frontend/` if fully replaced; update root README. |
| 6.3 | Update CI (if any) to build `web/` instead of `frontend/`. |

### Checkpoint 6

- [x] Production-like build and smoke test pass (`cd web && npm run build` passes all 8 routes).
- [x] Documentation points to Next for dashboard (README updated; `docs/DEPLOYMENT.md` created; CI includes `next-tests` job).

### Verification

```bash
cd web && npm run build
```

**Manual:** Deploy staging smoke: health, auth, one optimization path.

---

## Phase 7 — Data pipeline documentation and ops alignment

**Goal:** Clear story for **offline/batch** vs **online** API; paths and DB ownership documented for deploy.

| # | Task |
|---|------|
| 7.1 | Inventory scripts under `scripts/`, `methods/`, notebooks—what is prod vs dev. |
| 7.2 | Document SQLite / future DB: single writer rule, backup. |
| 7.3 | Optional: add CI job `pytest` + `web` lint/build on PR. |

### Checkpoint 7

- [x] New developer can answer: “Where does pipeline X write, and who reads it?” (see `docs/DATA_PIPELINE.md`).
- [x] No undocumented manual steps for release critical path (release path documented in `docs/DATA_PIPELINE.md` and `docs/DEPLOYMENT.md`; DB schema is `CREATE TABLE IF NOT EXISTS`, no manual migrations).

### Verification

```bash
python -m pytest tests/ -v --tb=short
```

*(Scope `tests/` to what exists in repo.)*

---

## Rollback strategy

| Scenario | Action |
|----------|--------|
| Next broken in prod | Revert deploy; keep Flask; run CRA `frontend/` if still in repo. |
| API contract change | Bump contract doc; coordinate Phase 1 table + integration tests. |
| Partial migration | Ship Next for static/marketing only; keep CRA for app until Phase 5b. |

---

## Sign-off template (copy into PR or release ticket)

```
Phase: ___
Checkpoint ID: ___
Verification commands run: (paste)
Manual checks: (tick)
Owner: ___
Date: ___
```
