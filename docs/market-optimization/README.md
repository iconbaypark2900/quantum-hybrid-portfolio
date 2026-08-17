# Market Optimization Project — Improvement Docs

This folder turns the market optimization improvement plan into repo-ready documentation.

The target project is a **reproducible market optimization lab** that compares classical, quantum-inspired, and quantum-routed portfolio solvers under realistic market data, constraints, risk models, transaction costs, and benchmark reports.

## Document map

| File | Purpose |
|---|---|
| [`01_project_upgrade_brief.md`](01_project_upgrade_brief.md) | Executive-level improvement direction and repo positioning |
| [`02_target_architecture.md`](02_target_architecture.md) | Target module layout, service boundaries, and data flow |
| [`03_market_data_layer.md`](03_market_data_layer.md) | Tiingo-first provider abstraction, validation, caching, and corporate-action handling |
| [`04_risk_engine.md`](04_risk_engine.md) | Covariance, CVaR, drawdown, factor exposure, and regime-risk models |
| [`05_optimizer_benchmark_harness.md`](05_optimizer_benchmark_harness.md) | Unified solver interface for classical, QSW, QUBO, QAOA, VQE, and Braket paths |
| [`06_backtesting_and_experiments.md`](06_backtesting_and_experiments.md) | Walk-forward backtesting, costs, slippage, no-leakage checks, and experiment registry |
| [`07_quantum_execution_and_dgx.md`](07_quantum_execution_and_dgx.md) | Honest quantum labeling, simulator/QPU metadata, DGX Spark workflow, and run artifacts |
| [`08_implementation_roadmap.md`](08_implementation_roadmap.md) | First PR, sprint plan, tests, and acceptance criteria |

## North star

> Build a market optimization system that can justify every allocation with data quality, solver comparison, risk metrics, backtest evidence, and execution metadata.

## Core principle

Do not add more “quantum” until the repo can answer:

1. What data was used?
2. Which solver generated the allocation?
3. Which baseline did it beat?
4. What risk changed?
5. What happened after transaction costs and turnover?
6. Was execution classical, quantum-inspired, simulated quantum, or hardware quantum?

## Recommended first PR

```text
feat: add market data provider layer and validated optimizer result schema
```

Files to add first:

```text
services/market_data/base.py
services/market_data/yfinance_provider.py
services/market_data/tiingo_provider.py
services/market_data/validation.py
optimizers/schema.py
tests/test_market_data_validation.py
tests/test_optimization_result_schema.py
docs/market-optimization/
```
