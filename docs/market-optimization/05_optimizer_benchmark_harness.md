# Optimizer Benchmark Harness

## Purpose

The optimizer harness makes every solver comparable.

The repo should support classical, quantum-inspired, and quantum-routed solvers, but they should all return the same result type.

## Target solver families

```text
optimizers/
  schema.py
  router.py

  classical/
    equal_weight.py
    min_variance.py
    max_sharpe.py
    risk_parity.py
    hrp.py
    black_litterman.py
    cvar.py

  quantum_inspired/
    qsw.py
    qubo_simulated_annealing.py

  quantum/
    qaoa_qiskit.py
    braket_annealing.py
    vqe_risk.py
```

## Unified result schema

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class OptimizationResult:
    solver_name: str
    execution_mode: str
    weights: dict[str, float]

    expected_return: float
    volatility: float
    sharpe: float
    sortino: float
    cvar_95: float
    max_drawdown: float
    turnover: float
    concentration_hhi: float

    objective_value: float | None
    constraints_satisfied: bool
    metadata: dict[str, Any]
```

## Solver interface

```python
import pandas as pd


class PortfolioSolver:
    name: str
    execution_mode: str

    def solve(
        self,
        returns: pd.DataFrame,
        previous_weights: dict[str, float] | None = None,
        constraints: dict | None = None,
    ) -> OptimizationResult:
        raise NotImplementedError
```

## Solver router

```python
class OptimizerRouter:
    def __init__(self, solvers: dict[str, PortfolioSolver]):
        self.solvers = solvers

    def solve(self, solver_name: str, returns, previous_weights=None, constraints=None):
        if solver_name not in self.solvers:
            available = ", ".join(sorted(self.solvers))
            raise ValueError(f"Unknown solver '{solver_name}'. Available: {available}")

        return self.solvers[solver_name].solve(
            returns=returns,
            previous_weights=previous_weights,
            constraints=constraints or {},
        )

    def compare(self, solver_names, returns, previous_weights=None, constraints=None):
        return [
            self.solve(name, returns, previous_weights, constraints)
            for name in solver_names
        ]
```

## Baseline solvers

### Equal weight

Algorithm type:

- Naive diversification baseline

Why it matters:

- Every complex optimizer should beat or justify failing against equal weight.

### Minimum variance

Algorithm type:

- Convex quadratic optimization

Why it matters:

- Tests covariance quality.

### Max Sharpe

Algorithm type:

- Mean-variance optimization

Why it matters:

- Classic portfolio objective.

### HRP

Algorithm type:

- Hierarchical clustering allocation

Why it matters:

- Strong robust baseline that avoids direct covariance inversion.

### CVaR

Algorithm type:

- Tail-risk optimization

Why it matters:

- More practical than volatility-only objectives.

### Risk parity

Algorithm type:

- Equal risk contribution optimization

Why it matters:

- Controls portfolio risk contribution by asset.

## Quantum-inspired solvers

### QSW

Algorithm type:

- Graph-based quantum-inspired stochastic walk

Use case:

- Converts market similarity or dependency graph into allocation dynamics.

Suggested metadata:

```json
{
  "graph_method": "correlation",
  "hamiltonian_type": "laplacian",
  "walk_time": 1.5,
  "decoherence_rate": 0.2,
  "normalization": "long_only_sum_to_one"
}
```

### QUBO simulated annealing

Algorithm type:

- Quadratic unconstrained binary optimization
- Simulated annealing

Use case:

- Discrete asset selection and constrained allocation.

## Quantum-routed solvers

### QAOA

Algorithm type:

- Variational quantum algorithm for combinatorial optimization

Use case:

- Small-N asset selection, cardinality constraints, QUBO optimization.

### VQE

Algorithm type:

- Variational eigensolver

Use case:

- Research path for Hamiltonian-encoded optimization objectives.

### Braket annealing

Algorithm type:

- Quantum annealing or managed quantum execution path

Use case:

- External quantum backend demo and benchmark comparison.

## Benchmark table

Every run should emit a table like:

| Solver | Mode | Sharpe | CVaR 95 | Max DD | Turnover | Cost Adj CAGR | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| Equal Weight | classical_only | 0.62 | 0.048 | -0.31 | 0.00 | 8.1% | Baseline |
| HRP | classical_only | 0.77 | 0.039 | -0.24 | 0.08 | 10.4% | Strong baseline |
| CVaR | classical_only | 0.81 | 0.033 | -0.21 | 0.12 | 10.9% | Best risk |
| QSW | quantum_inspired | 0.74 | 0.037 | -0.23 | 0.10 | 9.8% | Lower drawdown |
| QAOA | quantum_simulator | 0.69 | 0.043 | -0.27 | 0.15 | 8.9% | Small-N test |

## Constraint checks

Every solver should validate:

- Sum of weights equals 1
- No negative weights unless shorting is enabled
- Max weight is respected
- Turnover cap is respected
- Cardinality constraint is respected
- No NaN weights
- No missing ticker weights

## Tests

### `tests/test_solver_contracts.py`

Required tests:

- Every solver returns `OptimizationResult`
- Weights sum to 1
- No invalid tickers are returned
- Metadata includes `execution_mode`
- Constraint violations are caught
- Solver comparison table sorts correctly

## Acceptance criteria

The harness is complete when:

- QSW is one solver among many, not a one-off path
- All solvers return `OptimizationResult`
- Dashboard can compare solvers without custom code
- Baselines are always included in benchmark reports
- Quantum solvers are labeled by execution mode
