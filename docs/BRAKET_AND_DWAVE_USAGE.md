# Amazon Braket and D-Wave Usage in the Codebase

> **Last updated: April 2026**
> This document supersedes earlier versions that incorrectly stated no Braket integration existed.

---

## Status summary

| Platform | Integration Status | Code location |
|----------|--------------------|---------------|
| **Amazon Braket (D-Wave QPU)** | **Active** — real hardware + mock + classical fallback | `services/braket_backend.py` |
| **D-Wave (via Braket)** | **Ready / pending device validation** — see below | `services/braket_backend.py` |
| **D-Wave (direct SDK)** | ❌ No direct integration — all D-Wave access goes through Braket | — |

---

## Amazon Braket

### How it works

`objective = "braket_annealing"` submitted to `POST /api/portfolio/optimize` routes through:

```
api/app.py  (line ~1083-1088)
  └─ services/portfolio_optimizer.py :: run_optimization
        └─ services/braket_backend.py :: BraketAnnealingOptimizer.optimize
              ├─ _execute_mock       (BRAKET_USE_MOCK=true  or no device_arn)
              ├─ _execute_braket     (BRAKET_USE_MOCK=false + BRAKET_DEVICE_ARN set)
              └─ _classical_fallback (SDK absent or device failure)
```

> **Note:** `api/app.py` contains a legacy objective mapping that redirects
> `braket_annealing` → `qubo_sa` in some response metadata for backward compatibility.
> The actual optimization **does** attempt Braket when `BRAKET_ENABLED=true` and the SDK
> is installed — only the `backend_type` label in the API response was affected by the
> legacy mapping. This is now documented in the API reference.

### Key files

| File | Purpose |
|------|---------|
| `services/braket_backend.py` | `BraketAnnealingOptimizer` — QUBO construction, Ising conversion, mock, real-device dispatch |
| `services/portfolio_optimizer.py` | Routes `braket_annealing` to `BraketAnnealingOptimizer` |
| `services/tenant_integrations.py` | `save_braket_metadata` / `load_braket_metadata` (per-tenant preference JSON in SQLite) |
| `api/app.py` | `GET /api/config/integrations` — Braket status; `POST /api/config/braket/smoke-test` |
| `tests/test_braket_real_device.py` | Pytest-based unit tests (10 mock tests + 1 real-device test) |
| `scripts/braket_validate.py` | End-to-end validation script (mock → real device ladder) |
| `docs/BRAKET_AWS_SETUP.md` | AWS account setup, IAM, S3, cost guardrails |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRAKET_ENABLED` | `false` | Enable Braket integration |
| `BRAKET_USE_MOCK` | `true` | Use mock/classical path; set `false` for real QPU |
| `BRAKET_DEVICE_ARN` | _(unset)_ | D-Wave QPU device ARN (required for real runs) |
| `BRAKET_S3_BUCKET` | _(unset)_ | S3 bucket for task results (required for real runs) |
| `BRAKET_AWS_REGION` | `us-east-1` | AWS region |
| `BRAKET_SHOTS` | `100` | Number of annealing reads per task |
| `BRAKET_TIMEOUT` | `300` | Task timeout in seconds |

### API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/portfolio/optimize` | POST | Use `"objective": "braket_annealing"` |
| `GET /api/config/integrations` | GET | Shows Braket `configured` / `env_enabled` status |
| `POST /api/config/braket/smoke-test` | POST | QUBO smoke test (mock or real); requires `X-API-Key` |

---

## D-Wave (via Braket)

D-Wave QPU access is **entirely through Amazon Braket** — there is no direct `dwave-ocean-sdk`
dependency. The SDK submits an Ising problem (`braket.annealing.Problem`) to the device ARN.

**Current validation status:** The code path compiles and the Ising submission logic has been
corrected to use `braket.annealing.Problem` (not bare keyword args). Real-device validation
is pending account/device access — see `docs/BRAKET_AWS_SETUP.md` for instructions.

### SDK correctness (fixed April 2026)

The original `_execute_braket` used incorrect bare keyword args to `device.run()`.
It has been updated to use:

```python
from braket.annealing import Problem, ProblemType
problem = Problem(ProblemType.ISING, linear=h_dict, quadratic=J_dict)
task = self._device.run(problem, s3_destination_folder=(...), shots=...)
result = task.result()
# Annealing results use result.record_array, not result.measurements
```

### Problem size limits

| Device | Physical qubits | Practical QUBO (dense, no embedding) |
|--------|-----------------|--------------------------------------|
| Advantage_system6 | ~5,000 | ≤ ~20 variables (dense, no minor-embedding) |
| Advantage_system4 | ~5,000 | similar |

The current implementation uses a simplified qubit mapping (`i → i`) without minor-embedding.
For production use with larger portfolios, `dwave-networkx` embedding is required.

---

## Running validation

```bash
# Step 1–2: imports + mock (no AWS)
BRAKET_ENABLED=true BRAKET_USE_MOCK=true \
  python3 scripts/braket_validate.py --mock-only --n 5 --seed 42

# Step 3: real D-Wave device
BRAKET_ENABLED=true BRAKET_USE_MOCK=false \
  BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6 \
  BRAKET_S3_BUCKET=your-bucket \
  python3 scripts/braket_validate.py --n 5 --seed 42 \
    --output artifacts/braket_run_$(date +%Y%m%d).json

# Unit tests (no AWS required)
python3 -m pytest tests/test_braket_real_device.py -v -m braket_mock

# Real-device unit test (AWS required)
BRAKET_REAL_DEVICE_TEST=1 \
  python3 -m pytest tests/test_braket_real_device.py -v -m braket_real
```

---

## Future work

- Minor-embedding via `dwave-networkx` for larger portfolios (> ~20 assets dense).
- Validate first real D-Wave job; update `docs/next-phase/ENGINEERING_BACKLOG.md`.
- Consider `POST /api/config/braket/smoke-test` for operator-triggered validation.
