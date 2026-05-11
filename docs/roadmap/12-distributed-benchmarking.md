# 12 — Distributed Benchmarking Harness

**Priority:** Medium  
**Status:** Listed in Engineering Backlog as `⏭️ Pending` with note "Implement distributed benchmarking"  
**Area:** Backend `api/`, `services/`; Frontend Simulations page

---

## Problem

The core research proposition of this platform is that quantum-enhanced objectives outperform classical ones on specific portfolio optimization tasks. Currently there is no way to verify or demonstrate this claim within the platform itself because:

- Each optimization run uses a single backend
- There is no endpoint to run the same portfolio spec across multiple backends simultaneously and compare results
- Results from different runs (different sessions, different days) are not stored in a way that enables apples-to-apples comparison
- The Simulations page uses heuristic numbers, not actual multi-backend benchmark data

A benchmarking harness is necessary to produce machine-readable evidence of quantum advantage (or lack thereof), as required by the workspace rule: *"Store comparison outputs in machine-readable form (CSV/JSON) for later analysis."*

---

## Scope

**In scope:**
- `POST /api/benchmark/run` — accepts a portfolio spec and a list of backend/objective targets; runs all in parallel; returns comparison table
- Backends/objectives to compare: `markowitz`, `hrp`, `equal_weight`, `qubo_sa`, `vqe` (simulator), `qaoa` (simulator), `hybrid`
- Machine-readable output: JSON and CSV artifact written to `data/benchmarks/`
- Background job support (large benchmarks) using job queue from `04-quantum-job-queue.md`
- Frontend: benchmark comparison table in Simulations page with sortable columns

**Out of scope:**
- Real quantum hardware benchmarking (requires credentials; add as an optional backend flag)
- Statistical significance testing across repeated runs (parking lot)
- Cross-portfolio benchmarking (fixed portfolio spec per run for now)

---

## Affected Files

| File | Change |
|------|--------|
| `api/app.py` | Add `POST /api/benchmark/run` and `GET /api/benchmark/runs` |
| `services/benchmark.py` | Add `run_multi_backend_benchmark()` function |
| `data/benchmarks/` | Directory for JSON/CSV artifacts |
| `web/src/app/(ledger)/simulations/page.tsx` | Add benchmark comparison table |
| `web/src/lib/api.ts` | Add `runBenchmark(params)`, `listBenchmarkRuns()` |

---

## API Design

### Request: `POST /api/benchmark/run`

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "start_date": "2022-01-01",
  "end_date": "2024-12-31",
  "objectives": ["markowitz", "hrp", "qubo_sa", "vqe", "hybrid"],
  "constraints": { "weight_min": 0.02, "weight_max": 0.25 },
  "shots": 1024,
  "seed": 42,
  "async": false
}
```

If `async=true`, returns `{ "benchmark_id": "uuid-..." }` immediately and runs in background.  
If `async=false` (default for small configs), runs synchronously and returns results directly.

### Response

```json
{
  "benchmark_id": "uuid-...",
  "created_at": "2026-04-16T10:00:00Z",
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "results": [
    {
      "objective": "markowitz",
      "backend": "classical",
      "sharpe_ratio": 1.21,
      "expected_return": 0.18,
      "volatility": 0.15,
      "max_drawdown": -0.14,
      "solve_time_s": 0.03,
      "n_active": 5,
      "weights": { "AAPL": 0.28, ... }
    },
    {
      "objective": "vqe",
      "backend": "simulator",
      "sharpe_ratio": 1.35,
      "expected_return": 0.20,
      "volatility": 0.15,
      "max_drawdown": -0.12,
      "solve_time_s": 4.2,
      "n_active": 4,
      "circuit_metadata": { "depth_transpiled": 88, ... },
      "weights": { "AAPL": 0.30, ... }
    }
  ],
  "summary": {
    "best_sharpe": { "objective": "vqe", "value": 1.35 },
    "fastest": { "objective": "markowitz", "solve_time_s": 0.03 },
    "most_diversified": { "objective": "hrp", "n_active": 5 }
  },
  "artifact_paths": {
    "json": "data/benchmarks/benchmark-uuid-....json",
    "csv": "data/benchmarks/benchmark-uuid-....csv"
  }
}
```

---

## Benchmark Service Implementation

```python
# services/benchmark.py

import concurrent.futures
import time

def run_single_objective(spec: dict, objective: str) -> dict:
    t0 = time.perf_counter()
    result = portfolio_optimizer.optimize(
        tickers=spec['tickers'],
        objective=objective,
        constraints=spec['constraints'],
        seed=spec.get('seed', 42),
    )
    solve_time = time.perf_counter() - t0
    return {
        'objective': objective,
        'backend': 'classical' if objective in ('markowitz', 'hrp', 'equal_weight') else 'simulator',
        'solve_time_s': round(solve_time, 3),
        **result,
    }

def run_multi_backend_benchmark(spec: dict) -> list[dict]:
    objectives = spec.get('objectives', ['markowitz', 'hrp', 'vqe', 'hybrid'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(run_single_objective, spec, obj): obj for obj in objectives}
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append({'objective': futures[future], 'error': str(e)})
    return sorted(results, key=lambda r: r.get('sharpe_ratio', 0), reverse=True)
```

---

## Artifact Persistence

After each benchmark run, write two files to `data/benchmarks/`:

```python
import json, csv, os

def save_benchmark_artifacts(benchmark_id: str, results: list[dict]) -> dict:
    os.makedirs('data/benchmarks', exist_ok=True)
    json_path = f'data/benchmarks/benchmark-{benchmark_id}.json'
    csv_path = f'data/benchmarks/benchmark-{benchmark_id}.csv'
    
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    fieldnames = ['objective', 'backend', 'sharpe_ratio', 'expected_return',
                  'volatility', 'max_drawdown', 'solve_time_s', 'n_active']
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    return {'json': json_path, 'csv': csv_path}
```

---

## Frontend — Benchmark Comparison Table

Add to `web/src/app/(ledger)/simulations/page.tsx`:

```
[Run Benchmark]
Tickers: [session tickers]   Objectives: ☑ markowitz ☑ hrp ☑ vqe ☑ hybrid
                                                                     [Run]

[Benchmark Results]  (sorted by Sharpe)
Objective    Backend       Sharpe  Return  Vol    Drawdown  Solve Time
─────────────────────────────────────────────────────────────────────
vqe          simulator     1.35    20.1%  14.8%   -12%      4.2s   ⭐
hybrid       simulator     1.29    19.5%  15.1%   -13%      6.8s
markowitz    classical     1.21    18.0%  14.9%   -14%      0.0s
hrp          classical     1.15    16.2%  14.1%   -11%      0.1s

[Download CSV]  [Download JSON]
```

---

## Implementation Plan

1. **Add `run_multi_backend_benchmark()` to `services/benchmark.py`** (update the existing file if it exists, or create if empty).
2. **Add `POST /api/benchmark/run`** and **`GET /api/benchmark/runs`** to `api/app.py`.
3. **Add artifact directory** `data/benchmarks/` (add to `.gitignore`; add a `.gitkeep`).
4. **Add `runBenchmark()` and `listBenchmarkRuns()` to `web/src/lib/api.ts`**.
5. **Update Simulations page** with benchmark table and run form.
6. **Write tests**:
   - `test_benchmark_returns_all_objectives` — all requested objectives appear in results
   - `test_benchmark_artifact_written` — JSON and CSV files created in `data/benchmarks/`
   - `test_benchmark_error_objective_graceful` — if one objective fails, others still return

---

## Acceptance Criteria

- [ ] `POST /api/benchmark/run` returns comparison results for all requested objectives
- [ ] Machine-readable JSON and CSV artifacts written to `data/benchmarks/`
- [ ] Simulations page shows a sortable benchmark comparison table
- [ ] "Download CSV" button in UI downloads the artifact for the last benchmark run
- [ ] Failed individual objectives are reported with `error` field but do not abort the whole benchmark
- [ ] All three new tests pass

---

## Parking Lot

- Statistical significance testing: repeat each objective N times with different seeds, report mean/std Sharpe
- Real hardware benchmarking (requires IBM token; add `backend=hardware` flag)
- Cross-portfolio benchmarks (same objective, different universes)
- Automated benchmark on deploy (CI benchmark gate)
