# Track B: Quantum Hardware Integration

Provider matrix and milestones. Full roadmap: [planning/QUANTUM_INTEGRATION_ROADMAP.md](../planning/QUANTUM_INTEGRATION_ROADMAP.md). Braket/D-Wave usage: [BRAKET_AND_DWAVE_USAGE.md](../BRAKET_AND_DWAVE_USAGE.md).

**Code entry points:** `services/braket_backend.py`, `services/ibm_quantum.py`, `core/portfolio_optimizer.py` (API-facing optimization), `methods/` (VQE, QUBO-SA, etc.).

**Last updated:** March 24, 2026

## Provider Matrix

| Provider | Type | Algorithms | Code / integration | Status |
|----------|------|-------------|---------------------|--------|
| **IBM Quantum** | Gate-based (Qiskit) | VQE, QAOA (see objectives) | `services/ibm_quantum.py`, token via API | **Ready** — requires `IBM_QUANTUM_TOKEN` / runtime |
| **AWS Braket** | Annealing (+ optional gate) | QUBO / annealing path | `services/braket_backend.py` | **Ready** — mock by default; real device needs AWS + `BRAKET_DEVICE_ARN` |
| **D-Wave** | Annealing | Portfolio QUBO | Via Braket (Ising/QUBO mapping in `braket_backend`) | **Pending validation** on real device |
| **Google Quantum AI** | Gate-based | TBD | Not integrated | **Future** — roadmap only |
| **Simulators / classical fallbacks** | Local | All slow objectives | `methods/vqe.py`, `methods/qubo_sa.py`, etc. | **In use** — default path without cloud creds |

## Milestones (from QUANTUM_INTEGRATION_ROADMAP)

Roadmap phases are **product goals**, not calendar commitments. Track progress in [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md).

- [ ] **Phase 1**: Hybrid classical–quantum — QUBO asset selection, VQE risk, QAOA rebalancing (partially implemented in codebase)
- [ ] **Phase 2**: Full quantum optimization — QLSA, amplitude estimation, QML regime detection
- [ ] **Phase 3**: Advanced applications — Quantum Monte Carlo, distributed quantum

## Current State

- **Braket:** `BRAKET_ENABLED`, `BRAKET_USE_MOCK`, `BRAKET_S3_BUCKET`, `BRAKET_DEVICE_ARN` documented in `.env.example`; classical SA fallback when Braket unavailable.
- **IBM:** Set token via API where applicable; see IBM sections in `api.py` / `services/ibm_quantum.py`.
- **Real hardware:** [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md) — “Test with real quantum hardware” remains **pending** (needs AWS / IBM accounts and device access).

See [NEXT_STEPS.md § Future Enhancements](../NEXT_STEPS.md) for related enhancement bullets.

## Verification

**1. Imports / health (no cloud required)**

```bash
# From repository root
python -c "import services.braket_backend as b; print('braket_backend import OK')"
```

With API running:

```bash
curl -s http://127.0.0.1:5000/api/health | python -m json.tool
```

Confirm `checks` / `details` reflect Braket SDK and your local configuration.

**2. Mock Braket path (no AWS calls if mock is on)**

```bash
export BRAKET_ENABLED=true
export BRAKET_USE_MOCK=true
# start api.py then exercise an objective that routes to Braket if configured in optimizer
```

**3. Real device (only in a dedicated AWS account)**

- Configure AWS credentials, S3 bucket, device ARN per [BRAKET_AND_DWAVE_USAGE.md](../BRAKET_AND_DWAVE_USAGE.md).
- Record outcome in a PR or runbook; update backlog row to completed when validated.
