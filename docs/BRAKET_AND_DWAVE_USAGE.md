# Amazon Braket and D-Wave Usage in the Codebase

## Amazon Braket

**Note:** The project migrated from QSW/Braket to notebook-based methods. Braket-specific modules (`braket_backend.py`, `braket_estimator.py`) were removed.

### Current Status

| Component | Status |
|-----------|--------|
| `braket_annealing` objective | Maps to `qubo_sa` (classical simulated annealing) in `services/portfolio_optimizer.py` |
| Braket hardware | No integration — QUBO+SA runs classically |
| API | `POST /api/portfolio/optimize` with `objective=braket_annealing` returns QUBO-SA result |

### API & Services

| File | Usage |
|------|-------|
| `api.py` | `braket_annealing` maps to `qubo_sa` for backward compatibility |
| `services/portfolio_optimizer.py` | Legacy objective mapping: `braket_annealing` → `qubo_sa` |
| `core/optimizers/qubo_sa.py` | QUBO + Simulated Annealing (Orús et al. 2019) — classical |

---

## D-Wave

**No SDK or device integration** — D-Wave is only referenced in docs/comments.

| Location | Reference |
|----------|-----------|
| `notebooks/04_qubo_vqe_portfolio.ipynb` | Simulated annealing as "classical proxy for quantum annealing (D-Wave)" |
| `notebooks/05_hybrid_pipeline_grand_comparison.ipynb` | "D-Wave hybrid (n>500)" in timeline/legend |
| `QUANTUM_INTEGRATION_ROADMAP.md` | "Integrate D-Wave quantum annealing" as future task |

---

## Summary

| Platform | Integration Status |
|---------|--------------------|
| **Amazon Braket** | ❌ No integration — `braket_annealing` uses classical QUBO-SA |
| **D-Wave** | ❌ No integration — simulated annealing used as classical proxy only |

Future Braket/D-Wave integration would require re-adding a hardware backend that calls the respective APIs. The `qubo_sa` optimizer can be extended to dispatch to quantum hardware when configured.
