"""
GPU simulation tests for quantum circuit execution.

All tests are marked @pytest.mark.gpu and skipped unless GPU_TEST=1 is set.
No real quantum hardware is required — these test GPU-accelerated statevector
simulation only (PennyLane Lightning GPU or Qiskit Aer GPU).

Run:
    GPU_TEST=1 python3 -m pytest tests/test_gpu_simulation.py -v -m gpu

Skip:
    python3 -m pytest tests/ -v  (GPU tests silently skipped)
"""
import os
import json

import numpy as np
import pytest


gpu = pytest.mark.gpu


def _skip_if_no_gpu():
    if os.getenv("GPU_TEST", "0") != "1":
        pytest.skip(
            "Set GPU_TEST=1 and ensure a CUDA-capable GPU with pennylane-lightning[gpu] "
            "or qiskit-aer-gpu installed to run GPU tests."
        )


# ─────────────────────────────────────────────────────────────────────────────
# CPU baseline (always runs — establishes correctness reference)
# ─────────────────────────────────────────────────────────────────────────────

def test_pennylane_cpu_baseline_small_circuit():
    """CPU default.qubit baseline runs a small 4-qubit circuit without error."""
    try:
        import pennylane as qml
    except ImportError:
        pytest.skip("PennyLane is not installed")

    dev = qml.device("default.qubit", wires=4)

    @qml.qnode(dev)
    def circuit(params):
        for q in range(4):
            qml.RY(params[q], wires=q)
        for q in range(3):
            qml.CNOT(wires=[q, q + 1])
        return [qml.expval(qml.PauliZ(q)) for q in range(4)]

    rng = np.random.default_rng(42)
    params = rng.uniform(-np.pi, np.pi, 4)
    result = circuit(params)

    assert len(result) == 4
    assert all(-1.0 <= float(v) <= 1.0 for v in result), "Expectation values out of range"


# ─────────────────────────────────────────────────────────────────────────────
# GPU tests (skipped unless GPU_TEST=1)
# ─────────────────────────────────────────────────────────────────────────────

@gpu
def test_pennylane_lightning_gpu_available():
    """lightning.gpu device can be instantiated."""
    _skip_if_no_gpu()
    try:
        import pennylane as qml
    except ImportError:
        pytest.skip("PennyLane is not installed")

    try:
        dev = qml.device("lightning.gpu", wires=4)
        assert dev is not None
    except Exception as exc:
        pytest.fail(
            f"lightning.gpu device failed to initialize: {exc}\n"
            "Ensure pennylane-lightning[gpu] and cuQuantum are installed."
        )


@gpu
def test_pennylane_lightning_gpu_small_circuit():
    """lightning.gpu produces same expectation values as default.qubit for a small circuit."""
    _skip_if_no_gpu()
    try:
        import pennylane as qml
    except ImportError:
        pytest.skip("PennyLane is not installed")

    n = 4
    rng = np.random.default_rng(42)
    params = rng.uniform(-np.pi, np.pi, n)

    def make_circuit(dev):
        @qml.qnode(dev)
        def circuit(p):
            for q in range(n):
                qml.RY(p[q], wires=q)
            for q in range(n - 1):
                qml.CNOT(wires=[q, q + 1])
            return [qml.expval(qml.PauliZ(q)) for q in range(n)]
        return circuit

    cpu_dev = qml.device("default.qubit", wires=n)
    gpu_dev = qml.device("lightning.gpu", wires=n)

    cpu_result = np.asarray(make_circuit(cpu_dev)(params), dtype=float)
    gpu_result = np.asarray(make_circuit(gpu_dev)(params), dtype=float)

    np.testing.assert_allclose(
        gpu_result, cpu_result, atol=1e-5,
        err_msg="GPU and CPU results disagree beyond tolerance"
    )


@gpu
def test_pennylane_lightning_gpu_benchmark(tmp_path):
    """GPU simulation benchmark runs and produces a valid JSON artifact."""
    _skip_if_no_gpu()
    from scripts.gpu_sim_benchmark import run_benchmark

    result = run_benchmark(n=6, backend="lightning.gpu", seed=42, n_layers=2, n_evals=3)

    assert result["ok"] is True, f"GPU benchmark failed: {result.get('error')}"
    assert result["mean_elapsed_ms"] > 0
    assert result["n_qubits"] == 6
    assert len(result["expectation_values"]) == 6

    artifact_path = tmp_path / "gpu_bench.json"
    artifact_path.write_text(json.dumps(result, indent=2))
    loaded = json.loads(artifact_path.read_text())
    assert loaded["ok"] is True
    assert loaded["backend"] == "lightning.gpu"


@gpu
def test_qiskit_aer_gpu_available():
    """Qiskit AerSimulator GPU backend can be instantiated."""
    _skip_if_no_gpu()
    try:
        from qiskit_aer import AerSimulator
    except ImportError:
        pytest.skip("qiskit-aer-gpu is not installed")

    try:
        sim = AerSimulator(method="statevector", device="GPU")
        assert sim is not None
    except Exception as exc:
        pytest.fail(
            f"AerSimulator GPU failed to initialize: {exc}\n"
            "Ensure qiskit-aer-gpu (not qiskit-aer) is installed and a CUDA GPU is available."
        )


@gpu
def test_qiskit_aer_gpu_simple_circuit():
    """AerSimulator GPU runs a simple Bell-state circuit without error."""
    _skip_if_no_gpu()
    try:
        from qiskit_aer import AerSimulator
        from qiskit import QuantumCircuit
    except ImportError:
        pytest.skip("qiskit / qiskit-aer-gpu not installed")

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    sim = AerSimulator(method="statevector", device="GPU", shots=1024)
    job = sim.run(qc)
    result = job.result()
    counts = result.get_counts()

    # Bell state should give only |00> and |11>
    assert set(counts.keys()).issubset({"00", "11"})
    assert sum(counts.values()) == 1024
