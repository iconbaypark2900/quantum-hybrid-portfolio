# Implementation Roadmap

## Guiding principle

Build the boring foundation before adding more advanced quantum or agentic workflows.

The project becomes stronger when every run is:

- Validated
- Comparable
- Backtested
- Cost-adjusted
- Reproducible
- Dashboard-ready

## Phase 1 — Foundation PR

### PR title

```text
feat: add market data provider layer and optimizer result schema
```

### Files

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

### Acceptance criteria

- Tiingo and yfinance share one interface
- Optimizers cannot run on unvalidated data
- `OptimizationResult` exists
- Tests cover invalid price panels
- Docs are committed

## Phase 2 — Risk engine

### PR title

```text
feat: add risk engine with shrinkage covariance and CVaR metrics
```

### Files

```text
services/risk/schema.py
services/risk/covariance.py
services/risk/cvar.py
services/risk/drawdown.py
services/risk/concentration.py
tests/test_risk_engine.py
```

### Acceptance criteria

- Ledoit-Wolf covariance works
- OAS covariance works
- CVaR metric works
- Max drawdown works
- Concentration HHI works
- Every `OptimizationResult` includes risk fields

## Phase 3 — Solver harness

### PR title

```text
feat: standardize portfolio solvers behind benchmark harness
```

### Files

```text
optimizers/router.py
optimizers/classical/equal_weight.py
optimizers/classical/min_variance.py
optimizers/classical/hrp.py
optimizers/classical/cvar.py
optimizers/quantum_inspired/qsw.py
tests/test_solver_contracts.py
```

### Acceptance criteria

- Every solver returns `OptimizationResult`
- Solver comparison table works
- Weight constraints are checked
- QSW is benchmarked beside classical solvers
- Dashboard can consume the common result schema

## Phase 4 — Walk-forward backtesting

### PR title

```text
feat: add walk-forward backtesting with costs and turnover
```

### Files

```text
services/backtesting/walk_forward.py
services/backtesting/rebalance.py
services/backtesting/transaction_costs.py
services/backtesting/metrics.py
tests/test_backtest_no_leakage.py
```

### Acceptance criteria

- Lookback window excludes future data
- Monthly rebalancing works
- Transaction costs reduce returns
- Turnover is calculated correctly
- Benchmark comparison includes equal weight and SPY

## Phase 5 — Experiment registry

### PR title

```text
feat: add experiment registry and decision reports
```

### Files

```text
experiments/registry.py
experiments/schema.sql
services/reporting/decision_report.py
tests/test_experiment_registry.py
```

### Acceptance criteria

- Every run gets a `run_id`
- Config is stored
- Data-quality report is stored
- Solver metrics are stored
- Decision report is generated as Markdown

## Phase 6 — Quantum execution metadata

### PR title

```text
feat: add explicit quantum execution metadata and artifacts
```

### Files

```text
optimizers/quantum/execution_metadata.py
optimizers/quantum/qubo.py
optimizers/quantum/qaoa_qiskit.py
optimizers/quantum/artifact_store.py
tests/test_quantum_labeling.py
```

### Acceptance criteria

- QSW is labeled `quantum_inspired`
- QAOA simulator is labeled `quantum_simulator`
- Hardware routes require backend metadata
- QUBO artifact is stored
- Decoded allocation artifact is stored

## Phase 7 — Dashboard decision cockpit

### PR title

```text
feat: add optimizer comparison and risk decision dashboard
```

### Pages

```text
Overview
Data Quality
Optimizer Comparison
Risk Breakdown
Backtest
Quantum Runs
Rebalance Recommendation
Experiment Registry
```

### Acceptance criteria

- User can compare solvers
- Dashboard shows CVaR and drawdown
- Dashboard shows transaction-cost-adjusted returns
- Dashboard shows quantum execution mode
- Dashboard links to experiment artifacts

## First 10 tasks

| Priority | Task | Output |
|---:|---|---|
| 1 | Add `MarketDataProvider` protocol | Shared data interface |
| 2 | Add Tiingo provider | Primary data source |
| 3 | Add yfinance fallback provider | Demo/fallback source |
| 4 | Add data validation report | Trust layer |
| 5 | Add `OptimizationResult` | Shared solver schema |
| 6 | Add equal-weight baseline | Baseline comparison |
| 7 | Add Ledoit-Wolf covariance | Stable risk model |
| 8 | Add CVaR metric | Tail-risk reporting |
| 9 | Add solver router | Unified execution |
| 10 | Add solver contract tests | Prevent drift |

## Testing matrix

| Test file | Purpose |
|---|---|
| `test_market_data_validation.py` | Price panel quality |
| `test_optimization_result_schema.py` | Result schema stability |
| `test_risk_engine.py` | Risk metric correctness |
| `test_solver_contracts.py` | Solver interface compliance |
| `test_backtest_no_leakage.py` | Walk-forward correctness |
| `test_turnover_constraints.py` | Rebalance realism |
| `test_quantum_labeling.py` | Honest quantum metadata |
| `test_experiment_registry.py` | Reproducibility |

## Agent workflow with Liaison

Use Liaison to run the work as a conveyor belt:

```text
Planner Agent
  Defines PR scope and acceptance criteria

Data Agent
  Implements providers, validation, cache

Risk Agent
  Implements covariance, CVaR, drawdown, concentration

Optimization Agent
  Implements solver interface and baselines

Quantum Agent
  Adds QUBO/QAOA metadata and artifact handling

QA Agent
  Adds tests and no-leakage checks

Docs Agent
  Updates docs and decision reports
```

## Done definition

The upgrade is done when a user can run:

```bash
python scripts/run_solver_sweep.py \
  --universe emerging_tech \
  --solvers equal_weight,hrp,cvar,qsw,qaoa_simulator \
  --rebalance monthly \
  --lookback-days 252 \
  --transaction-cost-bps 10
```

And receive:

```text
Data quality report
Solver comparison table
Risk breakdown
Walk-forward backtest
Quantum execution metadata
Decision report
Reproduction command
Saved experiment artifacts
```
