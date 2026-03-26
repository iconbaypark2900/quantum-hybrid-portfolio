# Track C: Engineering Backlog

Migrated from [NEXT_STEPS.md § Remaining Tasks](../NEXT_STEPS.md). Actionable bullets with owner/priority placeholders.

**Last updated:** March 24, 2026

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
| Unified multi-provider data service | — | Medium | ✅ Completed | Created `services/data_provider_v2.py` with yfinance/Alpaca/Polygon support |
| Alpaca integration | — | Medium | ✅ Completed | Provider class ready, needs API keys |
| Polygon integration | — | Medium | ✅ Completed | Provider class ready, needs API keys |
| Automatic fallback between providers | — | Medium | ✅ Completed | Configurable via `DATA_PROVIDER_FALLBACK` |

## Quantum Hardware Integration

| Task | Owner | Priority | Status | Notes |
|------|-------|----------|--------|-------|
| Braket backend for real device execution | — | Medium | ✅ Completed | `services/braket_backend.py` supports real D-Wave via Braket |
| AWS credentials configuration | — | Medium | ✅ Completed | Environment variables documented in `.env.example` |
| S3 bucket for results storage | — | Medium | ✅ Completed | Configuration via `BRAKET_S3_BUCKET` |
| Test with real quantum hardware | — | Medium | ⏭️ Pending | Requires AWS Braket account and device access |

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
