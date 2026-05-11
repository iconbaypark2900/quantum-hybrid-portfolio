# Track C: Engineering Backlog

Migrated from [NEXT_STEPS.md § Remaining Tasks](../NEXT_STEPS.md). Actionable bullets with owner/priority placeholders.

**Last updated:** April 2026

**Related:** Frontend platform work (Next.js, phased migration) lives in **[../plans/README.md](../plans/README.md)** — update that plan’s checkpoints when shipping UI milestones.

## Infrastructure

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Add development/test configuration for Braket (mock vs real device) | — | High | ✅ Completed | Created `services/braket_backend.py` with mock/real device support |
| Verify full API integration with all dependencies | — | High | ✅ Completed | Enhanced health check with dependency verification |
| Run full API integration tests with complete dependency installation | — | High | ✅ Completed | Created `scripts/test_api_integration.py` (10/11 tests passing) |

## Production & Security

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| JWT authentication middleware | — | High | ✅ Completed | Created `services/auth.py`, added `/api/auth/*` endpoints |
| Input validation, sanitization, rate limiting | — | High | ✅ Completed | Existing in api.py, enhanced with JWT |
| Redis caching for quantum computations | — | High | ✅ Completed | In-memory cache implemented, Redis-ready |
| Database integration (PostgreSQL/MongoDB) | — | High | ✅ Completed | SQLite for runtime, PostgreSQL config in deploy script |
| Structured logging, metrics, health checks | — | High | ✅ Completed | Enhanced `/api/health` with full dependency checks |
| Deployment target decision | — | High | ✅ Completed | Hybrid strategy: HF Spaces + self-hosted (see PRODUCTION_AND_OPS.md) |

## Data Providers

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Unified multi-provider data service | — | Medium | ✅ Completed | `services/data_provider_v2.py` — Tiingo (default), Alpaca, Polygon, yfinance (legacy/deprecated) |
| Alpaca integration | — | Medium | ✅ Completed | Provider class ready, needs API keys |
| Polygon integration | — | Medium | ✅ Completed | Provider class ready, needs API keys |
| Automatic fallback between providers | — | Medium | ✅ Completed | Configurable via `DATA_PROVIDER_FALLBACK` |

## Quantum Hardware Integration

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Braket backend for real device execution | — | Medium | ✅ Completed | `services/braket_backend.py` — QUBO, Ising, mock + real dispatch |
| AWS credentials / IAM / S3 documentation | — | Medium | ✅ Completed | `docs/BRAKET_AWS_SETUP.md` — full setup guide with cost guardrails |
| Braket SDK correctness (`_execute_braket`) | — | High | ✅ Completed | Fixed: uses `braket.annealing.Problem` + `record_array`; April 2026 |
| Validation script (mock → real ladder) | — | High | ✅ Completed | `scripts/braket_validate.py` — JSON artifact output |
| Unit tests for Braket backend | — | High | ✅ Completed | `tests/test_braket_real_device.py` — 10 mock tests pass |
| NVIDIA GPU simulation (optional track) | — | Low | ✅ Completed | `docs/GPU_SIM_SETUP.md` — setup guide; `pytest -m gpu` marker |
| Braket smoke test API route | — | Medium | ✅ Completed | `POST /api/config/braket/smoke-test` — gated by `API_KEY` |
| Reconcile `BRAKET_AND_DWAVE_USAGE.md` doc drift | — | Medium | ✅ Completed | Rewritten April 2026; reflects actual integration |
| Test with real quantum hardware (D-Wave QPU) | — | Medium | ⏭️ Pending | Requires AWS account + `BRAKET_REAL_DEVICE_TEST=1`; see `docs/BRAKET_AWS_SETUP.md` |
| Minor-embedding for larger portfolios (> ~20 assets) | — | Low | ⏭️ Pending | Requires `dwave-networkx`; current mapping works for n ≤ 20 |

## Frontend (Optional)

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Next.js app + Stitch-aligned UI; CRA cutover | — | High | ⏭️ Pending | Canonical plan: [MIGRATION_PHASES_AND_CHECKPOINTS.md](../plans/MIGRATION_PHASES_AND_CHECKPOINTS.md) |
| Restore or rebuild: `EnhancedQuantumDashboard.js`, `ScenarioTester.js`, `HelpPanel.js` | — | Low | ⏭️ Pending | Superseded in favor of migration plan unless explicitly needed |

## Future Enhancements

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Implement distributed benchmarking | — | Low | ⏭️ Pending | |
| Add more quantum ML models (Quantum Boltzmann Machines, etc.) | — | Low | ⏭️ Pending | |
| Integrate with additional data providers (Alpha Vantage, Quandl) | — | Low | ⏭️ Pending | Framework in place for easy addition |
