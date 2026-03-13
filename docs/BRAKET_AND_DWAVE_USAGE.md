# Amazon Braket and D-Wave Usage in the Codebase

## Amazon Braket

Braket is **actively integrated** for quantum annealing and QAOA.

### Core Implementation

| File | Purpose |
|-----|---------|
| `core/quantum_inspired/braket_backend.py` | `BraketAnnealingOptimizer`, `run_braket_portfolio_optimization()`, `_run_on_braket()`, QUBO formulation. Uses `AwsDevice`, `Circuit`, `QuantumTask`. Falls back to classical QUBO when Braket is unavailable. |
| `core/quantum_inspired/qaoa_optimizer.py` | Braket as QAOA backend (`backend='braket'`). `_run_braket_qaoa()`, `_build_braket_qaoa_circuit()`. |
| `core/braket_estimator.py` | Estimates Braket runtime and cost (tasks, shots, wall-clock time) using official AWS QPU pricing. |

### API & Services

| File | Usage |
|-----|-------|
| `api.py` | `/api/braket/estimate` endpoint; `braket_annealing` objective. |
| `services/portfolio_optimizer.py` | `_run_braket_annealing()` for `braket_annealing` objective. |
| `core/quantum_inspired/hybrid_workflow.py` | `method == 'braket'` branch. |
| `services/benchmark.py` | `benchmark_braket()` method. |

### Dependencies

- `amazon-braket-sdk>=1.60.0`
- `amazon-braket-schemas>=1.18.0`

### Environment Variables

- `AWS_REGION` (default: us-east-1)
- `BRAKET_DEVICE_ARN`

---

## D-Wave

**No SDK or device integration** — D-Wave is only referenced in docs/comments.

| Location | Reference |
|----------|-----------|
| `notebooks/04_qubo_vqe_portfolio.ipynb` | Simulated annealing described as a "classical proxy for quantum annealing (D-Wave)". |
| `notebooks/05_hybrid_pipeline_grand_comparison.ipynb` | "D-Wave hybrid (n>500)" in timeline/legend. |
| `QUANTUM_INTEGRATION_ROADMAP.md` | "Integrate D-Wave quantum annealing" listed as a future task. |

---

## Summary

| Platform | Integration Status |
|----------|-------------------|
| **Amazon Braket** | ✅ Implemented — annealing backend with classical QUBO fallback; QAOA gate-based backend. |
| **D-Wave** | ❌ No integration — simulated annealing used as classical proxy only. |
