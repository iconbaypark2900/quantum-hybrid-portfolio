# Phase 5 — Critical user flows (Checkpoint 5a)

Reference: [MIGRATION_PHASES_AND_CHECKPOINTS.md](MIGRATION_PHASES_AND_CHECKPOINTS.md) — **Checkpoint 5a**: ≥50% of **critical** flows work in Next (`web/`).

**Last updated:** March 24, 2026

## Definition of “critical flow”

A **flow** is a **primary user goal** end-to-end in the Next app (load UI → optional API call → visible outcome). A flow counts as **working** when the happy path succeeds on a fresh dev setup (Flask on `:5000`, `NEXT_PUBLIC_API_URL` or proxy set, `cd web && npm run dev`).

## Flow inventory (by route)

| # | Route | Flow (short) | Notes |
|---|--------|----------------|--------|
| 1 | `/dashboard` | View health / KPIs / run sample optimization | Uses API for health + optimize |
| 2 | `/portfolio` | Portfolio Lab: simulated or **live** tickers → load data → backend optimize → weights / charts | Live path needs network + yfinance |
| 3 | `/strategy` | Load objectives & presets from API → pick method → preset → constraints → copy manifest | Config endpoints only |
| 4 | `/simulations` | Run **Scenario Comparison** → table of objectives vs API; stress cards (illustrative) | Needs API + yfinance for tickers |
| 5 | `/quantum` | Telemetry + IBM token (server-stored) + async jobs via `api.ts` | API health; jobs need `X-API-Key` |
| 6 | `/reports` | Select report type + format → **Generate & Download** (optimize → JSON/CSV) + preview | Error banner on failure; needs API |
| 7 | `/settings` | Settings stub | Placeholder OK for Phase 5 |
| 8 | `/health-check` | Proof: API health + smoke actions | |

**Total flows listed:** 8 (adjust list in PRs as routes gain parity).

## Measuring “≥50%”

1. **Numerator:** Count flows from the table above that pass a **manual smoke** (or automated test where it exists).
2. **Denominator:** Number of **non-stub** flows you have committed to for this release (exclude `/settings` if still “coming soon” only, or include it if you define a minimal “page loads” criterion).
3. **Example:** If denominator = 6, **≥50%** means **≥3** flows must pass.

Document in each Phase 5 PR: **which flows were verified** and how (checkboxes).

## Verification habit

- Backend: `python scripts/test_api_integration.py --base-url http://127.0.0.1:5000`
- Next: `cd web && npm run build && npm run lint && npm test`

## Related

- [WORKSTREAM_BREAKDOWN.md](WORKSTREAM_BREAKDOWN.md) — parallel workstreams
- [README.md](../next-phase/README.md) — `docs/next-phase` execution hub
