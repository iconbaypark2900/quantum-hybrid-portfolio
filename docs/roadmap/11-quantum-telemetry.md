# 11 — Quantum Circuit Telemetry in UI

**Priority:** Medium  
**Status:** Missing — IBM Quantum jobs submit and return optimization weights; no circuit metadata (depth, gate count, noise, fidelity) is returned or displayed  
**Area:** Backend `services/ibm_quantum.py`, `api/app.py`; Frontend `/quantum` page

---

## Problem

When an optimization is run via IBM Quantum (VQE, QAOA, hybrid_qaoa), the result is returned as portfolio weights. The UI has no visibility into:

- What circuit was executed (ansatz type, number of qubits, layers)
- Circuit depth and two-qubit gate count after transpilation
- Noise model or error rates of the target backend
- Transpilation time vs execution time breakdown
- Whether the result came from hardware or simulator
- Shot count and variance of the measurement outcomes

Without this data, quantum results are a black box. An institutional user cannot assess whether the quantum computation was reliable (deep circuits on noisy hardware produce garbage results), and the platform cannot differentiate itself from a classical optimizer with a quantum label.

---

## Scope

**In scope:**
- Extract and return circuit metadata in the IBM Quantum optimize response: `circuit_depth`, `gate_count`, `n_qubits`, `backend_name`, `shots`, `transpile_time_s`, `execute_time_s`, `noise_model_type`
- Store circuit metadata in the `optimization_runs` table (alongside the result)
- Display a "Quantum Telemetry" panel in the Quantum Engine page
- Display a circuit metadata summary card on individual run result pages

**Out of scope:**
- Visual circuit diagram rendering (ASCII or image) — complex, parking lot
- Gate-level fidelity and thermal relaxation rates (vendor-specific, requires IBM noise model query)
- Real-time hardware calibration data feed

---

## Affected Files

| File | Change |
|------|--------|
| `services/ibm_quantum.py` | Extract circuit metadata from Qiskit result object |
| `api/app.py` | Include `circuit_metadata` in optimize response |
| DB schema | Add `circuit_metadata` column (JSON) to `optimization_runs` |
| `web/src/app/(ledger)/quantum/page.tsx` | Add Quantum Telemetry panel |
| `web/src/app/(ledger)/reports/runs/[id]/page.tsx` | Show circuit metadata card for quantum runs |

---

## Circuit Metadata to Extract

From a Qiskit `EstimatorResult` or `SamplerResult` after transpilation:

```python
def extract_circuit_metadata(circuit, transpiled_circuit, result, backend_name, shots) -> dict:
    return {
        "n_qubits": circuit.num_qubits,
        "n_parameters": circuit.num_parameters,
        "depth_original": circuit.depth(),
        "depth_transpiled": transpiled_circuit.depth() if transpiled_circuit else None,
        "gate_count_original": dict(circuit.count_ops()),
        "gate_count_transpiled": dict(transpiled_circuit.count_ops()) if transpiled_circuit else None,
        "two_qubit_gate_count": transpiled_circuit.num_nonlocal_gates() if transpiled_circuit else None,
        "backend_name": backend_name,
        "shots": shots,
        "noise_model_type": "hardware" if "ibmq" in (backend_name or "") else "ideal_simulator",
    }
```

Timing is extracted around the `session.run()` call:
```python
t0 = time.perf_counter()
job = estimator.run(circuits, observables)
result = job.result()
execute_time_s = time.perf_counter() - t0
```

---

## API Response Addition

Append to the optimize response for IBM objectives:

```json
{
  "weights": { "AAPL": 0.25, ... },
  "sharpe_ratio": 1.42,
  "circuit_metadata": {
    "n_qubits": 8,
    "n_parameters": 32,
    "depth_original": 45,
    "depth_transpiled": 112,
    "two_qubit_gate_count": 28,
    "gate_count_transpiled": { "cx": 28, "rz": 64, "sx": 40 },
    "backend_name": "ibmq_qasm_simulator",
    "shots": 1024,
    "noise_model_type": "ideal_simulator",
    "transpile_time_s": 0.34,
    "execute_time_s": 2.18
  }
}
```

Non-IBM objectives (Markowitz, HRP, QUBO-SA) return `"circuit_metadata": null`.

---

## Frontend — Quantum Telemetry Panel

In `web/src/app/(ledger)/quantum/page.tsx`, add a new section below the connection status:

```
[Quantum Circuit Telemetry]
Last IBM run: 2026-04-15 14:22 UTC

Qubits:         8       Depth (original):      45
Parameters:     32      Depth (transpiled):    112
Two-qubit gates: 28     Backend:    ibmq_qasm_simulator
Shots:          1024    Execution time:        2.18s
Noise model:    ideal_simulator
```

- Only shown when last run was an IBM objective
- Color-code depth: green (< 50), yellow (50–150), red (> 150) — deep circuits are unreliable on NISQ hardware
- Link "Learn about circuit depth" → internal docs or IBM docs

---

## Implementation Plan

1. **Update `services/ibm_quantum.py`** — wrap the circuit execution block to extract metadata:
   - Before `session.run()`: record `circuit.depth()`, `circuit.num_qubits()`, transpiled circuit stats
   - After `job.result()`: record execution time
   - Return `circuit_metadata` dict alongside weights in the service return value

2. **Update `api/app.py`** — include `circuit_metadata` in the optimize response body.

3. **Add `circuit_metadata` column** to `optimization_runs` table (from `03-persistent-run-history.md`):
   ```sql
   ALTER TABLE optimization_runs ADD COLUMN circuit_metadata TEXT;
   ```
   Store as JSON string.

4. **Update `web/src/lib/api.ts`** — the `OptimizeResponse` type should include:
   ```typescript
   interface CircuitMetadata {
     n_qubits: number;
     depth_original: number;
     depth_transpiled: number | null;
     two_qubit_gate_count: number | null;
     backend_name: string;
     shots: number;
     noise_model_type: string;
     execute_time_s: number;
   }
   ```

5. **Add Quantum Telemetry panel** to `web/src/app/(ledger)/quantum/page.tsx` — conditionally render if `circuit_metadata` is non-null in the last run.

6. **Add circuit metadata card** to `web/src/app/(ledger)/reports/runs/[id]/page.tsx` — show for quantum runs, hidden for classical runs.

7. **Write tests**:
   - `test_circuit_metadata_present_for_ibm_objective` — IBM optimize response includes `circuit_metadata`
   - `test_circuit_metadata_null_for_classical` — Markowitz response has `circuit_metadata: null`
   - `test_transpiled_depth_gte_original` — transpiled depth must be >= original (transpilation adds gates)

---

## Acceptance Criteria

- [ ] IBM optimize response includes `circuit_metadata` with all listed fields
- [ ] Classical optimizer responses return `circuit_metadata: null`
- [ ] Circuit metadata is stored in the DB alongside the run record
- [ ] Quantum Engine page shows a Telemetry panel with last-run circuit stats
- [ ] Circuit depth is color-coded (green / yellow / red) in the UI
- [ ] All three new tests pass

---

## Parking Lot

- ASCII circuit diagram in the run detail page (Qiskit's `circuit.draw(output='text')`)
- Gate-level noise rates from IBM backend calibration API
- Comparison: ideal simulator vs noisy simulator result for same circuit
- Alert if transpiled depth exceeds 200 (NISQ reliability threshold)
