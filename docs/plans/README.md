# Refactoring & migration plans

This folder holds **phased execution plans** for moving toward a **Next.js frontend**, a **clear Flask API boundary**, and an **explicit data-pipeline flow**. Use these documents for scheduling, checkpoints, and “definition of done.”

## Documents

| Document | Purpose |
|----------|---------|
| [MIGRATION_PHASES_AND_CHECKPOINTS.md](MIGRATION_PHASES_AND_CHECKPOINTS.md) | **Master sequence**: phases 0–7, checkpoints, automated/manual tests, sign-off criteria |
| [WORKSTREAM_BREAKDOWN.md](WORKSTREAM_BREAKDOWN.md) | **Parallel workstreams** (web, API, pipeline), dependencies, and suggested owners |

## How to use

1. **Sequential work**: Follow [MIGRATION_PHASES_AND_CHECKPOINTS.md](MIGRATION_PHASES_AND_CHECKPOINTS.md) in order unless a phase is explicitly marked optional or parallel-safe.
2. **Team parallelization**: Assign tracks from [WORKSTREAM_BREAKDOWN.md](WORKSTREAM_BREAKDOWN.md); resolve cross-track dependencies at each **checkpoint**.
3. **Quality bar**: No phase is complete until its **Verification** section passes (commands + manual checks).

## Related docs

- [docs/next-phase/README.md](../next-phase/README.md) — execution hub (production, quantum, backlog)
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) — current system architecture
- [docs/GETTING_STARTED.md](../GETTING_STARTED.md) — run API and dashboard
- [stitch_strategy_ml_config_market_optimization_new/](../../stitch_strategy_ml_config_market_optimization_new/) — UI mockups (HTML reference)

**Last updated:** March 24, 2026
