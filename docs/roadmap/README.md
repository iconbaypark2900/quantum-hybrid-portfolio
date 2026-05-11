# Roadmap: Changes Needed

This folder documents every incomplete, placeholder, or missing feature identified in the Quantum Hybrid Portfolio platform as of **April 2026**. Each file is a self-contained engineering spec covering what is broken or missing, the exact code locations affected, the deliverable, and an acceptance criteria checklist.

Files are numbered by priority — `01` is highest, `15` is lowest.

---

## Index

| # | File | Area | Priority |
|---|------|------|----------|
| 01 | [01-var-and-risk-models.md](01-var-and-risk-models.md) | Empirical VaR & correlation matrix | High |
| 02 | [02-constraint-passthrough.md](02-constraint-passthrough.md) | Constraint pass-through in all optimizers | High |
| 03 | [03-persistent-run-history.md](03-persistent-run-history.md) | Server-side run history & reproducibility | High |
| 04 | [04-quantum-job-queue.md](04-quantum-job-queue.md) | Async quantum job queue & live status | High |
| 05 | [05-portfolio-charting.md](05-portfolio-charting.md) | Portfolio time-series charting in UI | High |
| 06 | [06-walkforward-backtest.md](06-walkforward-backtest.md) | Walk-forward & rolling-window backtest | High |
| 07 | [07-pdf-reports.md](07-pdf-reports.md) | PDF report generation | Medium |
| 08 | [08-factor-models.md](08-factor-models.md) | Factor model integration (replace stubs) | Medium |
| 09 | [09-regime-detection.md](09-regime-detection.md) | Regime detection & adaptive strategy | Medium |
| 10 | [10-multi-tenant-ui.md](10-multi-tenant-ui.md) | Multi-tenant credential management UI | Medium |
| 11 | [11-quantum-telemetry.md](11-quantum-telemetry.md) | Quantum circuit telemetry in UI | Medium |
| 12 | [12-distributed-benchmarking.md](12-distributed-benchmarking.md) | Distributed benchmarking harness | Medium |
| 13 | [13-data-provider-transparency.md](13-data-provider-transparency.md) | Data provider transparency in UI | Medium |
| 14 | [14-hardware-integration.md](14-hardware-integration.md) | Real quantum hardware (D-Wave QPU, GPU sim, Google) | Low–Medium |
| 15 | [15-ops-slo-security.md](15-ops-slo-security.md) | Ops: SLIs/SLOs, encryption, alerting | Medium |

---

## How to Use These Docs

Each spec follows this structure:

1. **Status** — current state (placeholder / missing / partial)
2. **Problem** — what is broken or absent and why it matters
3. **Scope** — in-scope deliverable and explicit out-of-scope items
4. **Affected files** — exact paths and line numbers
5. **Implementation plan** — ordered steps
6. **Acceptance criteria** — testable checklist to close the ticket
7. **Parking lot** — follow-up ideas deferred from this change

---

## Relationship to Existing Docs

- Engineering backlog: [`docs/next-phase/ENGINEERING_BACKLOG.md`](../next-phase/ENGINEERING_BACKLOG.md)
- Quantum hardware matrix: [`docs/next-phase/QUANTUM_HARDWARE.md`](../next-phase/QUANTUM_HARDWARE.md)
- Feature manifest: [`docs/next-phase/QUANTUM_LEDGER_MANIFEST.md`](../next-phase/QUANTUM_LEDGER_MANIFEST.md)
- Production ops: [`docs/next-phase/PRODUCTION_AND_OPS.md`](../next-phase/PRODUCTION_AND_OPS.md)
- Migration plan: [`docs/plans/MIGRATION_PHASES_AND_CHECKPOINTS.md`](../plans/MIGRATION_PHASES_AND_CHECKPOINTS.md)

When a roadmap item is completed, update:
1. The checklist in its roadmap file (check the boxes)
2. `ENGINEERING_BACKLOG.md` status column
3. `AGENTS.md` if the change affects workspace facts
