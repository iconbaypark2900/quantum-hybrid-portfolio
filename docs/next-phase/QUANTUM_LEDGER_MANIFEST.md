# Quantum Ledger: Feature & Capabilities Manifest

**"The Quantum Ledger"** is the product experience name for this platform. Design north star: [`docs/design/DESIGN.md`](../design/DESIGN.md). Stitch HTML exports: `stitch_strategy_ml_config_market_optimization_new/`.

This document maps each manifest pillar to its implementation in the codebase.

## Pillar-to-route map

| Manifest Pillar | Next.js Route | Key API Endpoints |
|-----------------|---------------|-------------------|
| 1. Executive Intelligence | `/dashboard` | `/api/health`, `/api/portfolio/optimize` |
| 2. Strategy & ML Config | `/strategy` | `/api/config/objectives`, `/api/config/presets`, `/api/export/config` |
| 3. Simulation & Testing | `/simulations` | `/api/portfolio/optimize` (multi-objective comparison) |
| 4. Quantum Engine | `/quantum` | `/api/config/ibm-quantum/*`, `/api/jobs/*`, `/api/health` |
| 5. Reports & Export | `/reports` | `/api/export/audit-log`, `/api/export/audit-log/csv`, `/api/export/config` |
| Portfolio Lab (CRA parity) | `/portfolio` | All portfolio/optimize/backtest endpoints |

## Implementation status

| Phase | Scope | Status |
|-------|-------|--------|
| A. Platform & naming | Tailwind tokens, AppLayout, sidebar, route shell, manifest doc | Done |
| B. Executive intelligence | Dashboard page with KPIs, holdings, sector allocation, optimization feed | Done |
| C. Simulation & testing | Strategy comparison table, stress test cards | Done |
| D. Strategy / ML config | Objective/preset browser, constraint sliders, YAML manifest export | Done |
| E. Quantum ops & audit | IBM Quantum connection, job queue UI, engine telemetry, audit-log export endpoints | Done |
| F. Reports & export | Report type selector, JSON/CSV download, preview pane, backend audit-log endpoints | Done |

## Design alignment

The Next.js `web/` app uses tokens from [`docs/design/DESIGN.md`](../design/DESIGN.md) via Tailwind config (`ql-*` prefix). Fonts: Space Grotesk (headlines) + Inter (body) + JetBrains Mono (data). Surface hierarchy follows the "No-Line Rule" from the design spec.

## Future work (deferred)

- LSTM/Transformer ensemble training pipelines (ML platform work)
- SLM / sentiment ingestion + feature store
- Logic Canvas (visual node editor)
- PDF report generation
- Real quantum hardware telemetry (gate fidelity, thermal states) — requires vendor API payloads
