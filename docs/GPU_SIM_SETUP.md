# GPU-Accelerated Quantum Simulation Setup (NVIDIA)

This document covers using NVIDIA GPUs to accelerate the gate-based simulation
code paths already in the repository:

- `core/quantum_inspired/qaoa_optimizer.py` — QAOA via PennyLane
- `core/quantum_inspired/vqe_risk.py` — VQE via PennyLane
- `core/quantum_inspired/quantum_linear_algebra.py` — VQLS via PennyLane

**GPU is not required.** All code paths fall back to CPU simulation automatically.
GPU acceleration reduces runtime for larger circuits (n_assets ≥ 10) and is most
useful during local development or CI benchmarking.

---

## 1. Prerequisites

| Requirement | Detail |
|-------------|--------|
| NVIDIA GPU | Compute Capability ≥ 7.0 (Volta or newer: V100, A100, RTX 30/40 series) |
| CUDA Toolkit | ≥ 11.8 (for Lightning-GPU) or ≥ 12.0 (for Lightning-GPU 0.36+) |
| cuDNN | Version matching the CUDA toolkit |
| Python | ≥ 3.11 (project requirement) |

Check your CUDA version:

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
nvcc --version
```

---

## 2. Option A — PennyLane Lightning GPU (recommended)

PennyLane's `lightning.gpu` device provides GPU-accelerated statevector simulation.
Existing code using `qml.device("default.qubit", ...)` can be switched by changing
the device string to `"lightning.gpu"`.

### Install

```bash
# With venv active (do NOT install into system Python)
pip install pennylane-lightning[gpu]
```

> The package installs `PennyLane-Lightning-GPU` which depends on `cuQuantum`.
> If cuQuantum is not bundled, install separately:
> ```bash
> pip install cuquantum-python-cu12  # or cu11 for CUDA 11.x
> ```

### Verify

```bash
python3 -c "
import pennylane as qml
dev = qml.device('lightning.gpu', wires=4)
print('lightning.gpu available on:', dev.short_name)
"
```

### Benchmark a small VQE circuit

```bash
GPU_TEST=1 python3 -m pytest tests/test_gpu_simulation.py -v -m gpu
```

Or run the standalone benchmark:

```bash
GPU_TEST=1 python3 scripts/gpu_sim_benchmark.py --n 8 --backend lightning.gpu
```

---

## 3. Option B — Qiskit Aer GPU

Qiskit's `AerSimulator` supports GPU-backed statevector simulation for the IBM
VQE/QAOA paths that use Qiskit.

### Install

```bash
pip install qiskit-aer-gpu
```

> `qiskit-aer-gpu` replaces `qiskit-aer` and includes CUDA support.
> Do not install both — they conflict.

### Verify

```bash
python3 -c "
from qiskit_aer import AerSimulator
sim = AerSimulator(method='statevector', device='GPU')
print('Aer GPU simulator:', sim.name)
"
```

### Use in existing code

The IBM VQE path in `methods/vqe.py` uses `AerSimulator`. Switch to GPU by setting:

```bash
IBM_VQE_DEVICE=GPU  # checked in methods/vqe.py when building AerSimulator
```

---

## 4. Option C — CUDA Quantum (cudaq)

NVIDIA's `cudaq` library targets native CUDA Quantum kernels. This is **new integration work**,
not a drop-in acceleration of existing PennyLane/Qiskit code. Only relevant if the team
decides to standardize on the NVIDIA quantum stack.

Install:

```bash
pip install cudaq
```

Documentation: https://nvidia.github.io/cuda-quantum/

---

## 5. GPU benchmark / smoke test script

```bash
scripts/gpu_sim_benchmark.py --n 6 --backend default.qubit  # CPU baseline
scripts/gpu_sim_benchmark.py --n 6 --backend lightning.gpu  # GPU
```

The script runs a 2-layer PennyLane VQE circuit on a random n-asset problem,
times it, and writes a JSON summary.

```bash
usage: gpu_sim_benchmark.py [--n N] [--seed SEED] [--backend BACKEND] [--output OUTPUT]
  --n N            Number of qubits / assets (default: 6)
  --seed SEED      Random seed (default: 42)
  --backend BACKEND  PennyLane device string (default: default.qubit)
  --output OUTPUT  Path to write JSON artifact
```

---

## 6. Pytest marker

GPU tests are marked `@pytest.mark.gpu` and skipped by default. To run them:

```bash
# Set GPU_TEST=1 to enable gpu tests
GPU_TEST=1 python3 -m pytest tests/ -v -m gpu
```

The `gpu` marker is registered in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "gpu: tests that require a CUDA-capable GPU (set GPU_TEST=1 to enable)",
    ...
]
```

---

## 7. CI / deployment notes

- GPU tests are **not** expected to run in standard CI unless a GPU runner is provisioned.
- On CPU-only CI: `GPU_TEST` is unset → all `@pytest.mark.gpu` tests are automatically skipped.
- For benchmarking runs, save the JSON artifact from `gpu_sim_benchmark.py` as a
  machine-readable comparison (backend, n_qubits, elapsed_ms, device) per workspace conventions.

---

## 8. Related files

| File | Purpose |
|------|---------|
| `core/quantum_inspired/qaoa_optimizer.py` | PennyLane QAOA — switch device to `lightning.gpu` |
| `core/quantum_inspired/vqe_risk.py` | PennyLane VQE — switch device to `lightning.gpu` |
| `methods/vqe.py` | Qiskit Aer VQE — set `IBM_VQE_DEVICE=GPU` |
| `scripts/gpu_sim_benchmark.py` | GPU vs CPU benchmark (mock-safe, no real QPU) |
| `tests/test_gpu_simulation.py` | Pytest GPU tests (`-m gpu`, skipped without `GPU_TEST=1`) |

---

*Last updated: April 2026*
