# Market Optimization Project — Upgrade Brief

## Current project identity

The market optimization repo should be positioned as:

> A quantum-hybrid portfolio optimization lab that compares classical solvers, quantum-inspired graph allocation, and quantum-routed optimization under reproducible market data, risk constraints, and benchmark reports.

The repo already appears to have the correct high-level ingredients:

- QSW / quantum stochastic walk optimizer
- Classical objectives such as max Sharpe, min variance, HRP, risk parity, and target return
- Braket, QAOA, VQE, and quantum-hybrid placeholders
- Flask or FastAPI-style backend services
- React and/or Streamlit dashboards
- Backtesting and constraints modules
- DGX Spark suitability

The improvement is not “add more algorithms.” The improvement is to turn the repo into a **decision-grade benchmark system**.

## Main gap

The repo needs stronger proof infrastructure:

| Gap | Why it matters |
|---|---|
| Market data abstraction is likely too thin | Optimizer outputs are fragile if data is stale, split-adjusted incorrectly, or missing |
| Solver outputs are probably inconsistent | QSW, HRP, QAOA, and CVaR need one result schema |
| Risk is not central enough | Sharpe alone is not enough for a practical allocation engine |
| Backtesting needs strict walk-forward logic | Prevents lookahead leakage and fake performance |
| Quantum path needs honest labeling | Users must know whether a run used classical, simulator, or QPU execution |
| Experiment tracking needs to be first-class | Reproducibility requires configs, seeds, artifacts, and run metadata |

## Target system statement

Every portfolio recommendation should produce:

```json
{
  "allocation": {
    "NVDA": 0.18,
    "AMD": 0.12,
    "MSFT": 0.15,
    "GOOGL": 0.10
  },
  "solver": "cvar_turnover_constrained",
  "execution_mode": "classical_only",
  "data_provider": "tiingo",
  "lookback_days": 252,
  "rebalance_frequency": "monthly",
  "expected_return": 0.183,
  "volatility": 0.221,
  "sharpe": 0.83,
  "cvar_95": 0.041,
  "max_drawdown": -0.192,
  "turnover": 0.124,
  "transaction_cost_bps": 10,
  "benchmarks": {
    "equal_weight": {"sharpe": 0.62},
    "hrp": {"sharpe": 0.77},
    "qsw": {"sharpe": 0.74}
  }
}
```

## Upgrade thesis

The repo should compare three solver families:

| Family | Examples | Purpose |
|---|---|---|
| Classical | Equal weight, min variance, max Sharpe, HRP, CVaR, risk parity, Black-Litterman | Strong baselines |
| Quantum-inspired | QSW, QUBO with simulated annealing | Fast local experiments with quantum-style formulation |
| Quantum-routed | QAOA, VQE, Braket, IBM Runtime | Research-grade experiments and demos |

## What “better” means

A better repo should optimize for:

1. **Correctness** — no leakage, no bad price data, no inconsistent weights.
2. **Comparability** — every solver returns the same schema.
3. **Risk awareness** — tail risk, drawdown, turnover, and concentration matter.
4. **Reproducibility** — every run stores config, seed, data range, artifacts, and metrics.
5. **Explainability** — dashboard explains why a solver won or lost.
6. **Quantum honesty** — simulator and hardware runs are explicitly labeled.

## Recommended first milestone

Build the foundation before expanding solver complexity:

```text
Milestone 1: Data + schema + baseline comparison
```

Deliverables:

- Market data provider abstraction
- Tiingo primary provider
- yfinance fallback provider
- Data validation report
- Unified `OptimizationResult`
- Equal-weight, HRP, max-Sharpe, and QSW comparison
- First benchmark table in dashboard
