# Track B: Quantum Hardware Integration

Provider matrix and milestones. Full roadmap: [planning/QUANTUM_INTEGRATION_ROADMAP.md](../planning/QUANTUM_INTEGRATION_ROADMAP.md).
Braket/D-Wave setup: [BRAKET_AND_DWAVE_USAGE.md](../BRAKET_AND_DWAVE_USAGE.md), [BRAKET_AWS_SETUP.md](../BRAKET_AWS_SETUP.md).

**Code entry points:** `services/braket_backend.py`, `services/ibm_quantum.py`, `core/portfolio_optimizer.py`, `methods/`.

**Last updated:** April 2026

---

## Provider Matrix

| Provider | Type | Algorithms | Code / integration | Status |
|----------|------|-------------|---------------------|--------|
| **IBM Quantum** | Gate-based (Qiskit) | VQE, QAOA | `services/ibm_quantum.py`, token via API | **Ready** — requires `IBM_QUANTUM_TOKEN` / runtime |
| **AWS Braket / D-Wave** | Annealing (QPU) | Portfolio QUBO (Ising) | `services/braket_backend.py` | **SDK fixed** — mock path verified; real QPU pending account access |
| **NVIDIA GPU simulation** | Gate-based (CPU/GPU sim) | VQE / QAOA via PennyLane Lightning or Qiskit Aer | See GPU track below | **Optional** — no GPU required; `pytest -m gpu` skipped by default |
| **Google Quantum AI** | Gate-based | TBD | Not integrated | **Future** — roadmap only |
| **Simulators / classical fallbacks** | Local CPU | All objectives | `methods/vqe.py`, `methods/qubo_sa.py`, etc. | **In use** — default without cloud creds |

---

## Milestones (from QUANTUM_INTEGRATION_ROADMAP)

Roadmap phases are product goals, not calendar commitments. Track progress in [ENGINEERING_BACKLOG.md](ENGINEERING_BACKLOG.md).

- [ ] **Phase 1**: Hybrid classical–quantum — QUBO asset selection, VQE risk, QAOA rebalancing (code present; needs real-device validation)
- [ ] **Phase 2**: Full quantum optimization — QLSA, amplitude estimation, QML regime detection
- [ ] **Phase 3**: Advanced applications — Quantum Monte Carlo, distributed quantum

---

## Current State (April 2026)

### AWS Braket / D-Wave

- **SDK:** `amazon-braket-sdk` is an optional dependency. Project imports with graceful fallback to classical SA.
- **Implementation:** `services/braket_backend.py` (`BraketAnnealingOptimizer`) — QUBO build, QUBO→Ising, mock execution, real-device dispatch.
- **SDK fix (April 2026):** `_execute_braket` was updated to use `braket.annealing.Problem` (correct for D-Wave via Braket) and `result.record_array` (annealing result format). Previous version incorrectly used bare `device.run(problem_type=...)` keyword args (gate-based API).
- **Validation script:** `scripts/braket_validate.py` — runs mock → real device ladder, emits machine-readable JSON artifact.
- **Unit tests:** `tests/test_braket_real_device.py` — 10 mock tests pass; 1 real-device test (`-m braket_real`) skipped by default.
- **Real device:** Pending — requires AWS account, D-Wave QPU access, and `BRAKET_REAL_DEVICE_TEST=1`.

### IBM Quantum

- Token stored per tenant via API; see IBM sections in `services/ibm_quantum.py`.
- Smoke test: `POST /api/config/ibm-quantum/smoke-test`.

### NVIDIA GPU simulation (optional)

- No GPU-specific code in the repo today. Gate-based VQE/QAOA paths use PennyLane + Qiskit on CPU.
- GPU acceleration is available via `pennylane-lightning[gpu]` (CUDA) or `qiskit-aer-gpu`.
- Setup: see [GPU_SIM_SETUP.md](../GPU_SIM_SETUP.md).
- Tests: `pytest -m gpu` (skipped unless `GPU_TEST=1`).

---

## Verification commands

```bash
# 1. Import check (no AWS)
python3 -c "import services.braket_backend as b; print('import OK')"

# 2. Unit tests — mock path (no AWS, venv active)
python3 -m pytest tests/test_braket_real_device.py -v -m braket_mock

# 3. Mock → real ladder (no AWS)
BRAKET_ENABLED=true BRAKET_USE_MOCK=true \
  python3 scripts/braket_validate.py --mock-only --n 5 --seed 42

# 4. Real D-Wave device (requires AWS account + BRAKET_REAL_DEVICE_TEST=1)
BRAKET_ENABLED=true BRAKET_USE_MOCK=false \
  BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6 \
  BRAKET_S3_BUCKET=your-bucket \
  python3 scripts/braket_validate.py --n 5 --seed 42 \
    --output artifacts/braket_run_$(date +%Y%m%d).json

# 5. API health check (API running)
curl -s http://127.0.0.1:5000/api/health | python3 -m json.tool | grep -E '"braket"'
```

When a real-device run succeeds, update `ENGINEERING_BACKLOG.md` and record the artifact path.
