#!/usr/bin/env python3
"""
GPU vs CPU benchmark for PennyLane quantum simulation.

Runs a 2-layer parameterized VQE-shaped circuit on an n-qubit system and
compares elapsed time between the chosen PennyLane backend (default.qubit for
CPU baseline, lightning.gpu for GPU).

No real quantum hardware required — this is purely a simulation benchmark.

Usage:
    # CPU baseline
    python3 scripts/gpu_sim_benchmark.py --n 6 --backend default.qubit

    # GPU (requires pennylane-lightning[gpu] + CUDA GPU)
    python3 scripts/gpu_sim_benchmark.py --n 6 --backend lightning.gpu

    # Save artifact
    python3 scripts/gpu_sim_benchmark.py --n 8 --backend lightning.gpu \\
        --output artifacts/gpu_bench_$(date +%Y%m%d).json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _build_vqe_circuit(n_qubits: int, n_layers: int, backend: str):
    """
    Build a 2-layer strongly-entangled ansatz circuit using PennyLane.
    Returns (device, circuit_fn, n_params).
    """
    try:
        import pennylane as qml
    except ImportError:
        raise RuntimeError(
            "PennyLane is not installed. Run: pip install pennylane"
        )

    kwargs = {"wires": n_qubits}
    if backend == "lightning.gpu":
        kwargs["shots"] = None  # statevector simulation
    dev = qml.device(backend, **kwargs)

    n_params = n_layers * n_qubits * 3  # 3 rotations per qubit per layer

    @qml.qnode(dev)
    def circuit(params):
        p = params.reshape(n_layers, n_qubits, 3)
        for layer in range(n_layers):
            for q in range(n_qubits):
                qml.Rot(*p[layer, q], wires=q)
            for q in range(n_qubits - 1):
                qml.CNOT(wires=[q, q + 1])
        return [qml.expval(qml.PauliZ(q)) for q in range(n_qubits)]

    return dev, circuit, n_params


def run_benchmark(n: int, backend: str, seed: int, n_layers: int = 2, n_evals: int = 5) -> dict:
    """
    Run the VQE circuit `n_evals` times with fixed parameters and return timing.
    """
    rng = np.random.default_rng(seed)

    try:
        dev, circuit, n_params = _build_vqe_circuit(n, n_layers, backend)
    except Exception as exc:
        return {
            "ok": False,
            "backend": backend,
            "error": str(exc),
            "n_qubits": n,
        }

    params = rng.uniform(-np.pi, np.pi, n_params).astype(np.float64)

    # Warm-up
    try:
        _ = circuit(params)
    except Exception as exc:
        return {
            "ok": False,
            "backend": backend,
            "error": f"Circuit execution failed: {exc}",
            "n_qubits": n,
        }

    # Timed evals
    times = []
    for _ in range(n_evals):
        t0 = time.perf_counter()
        result = circuit(params)
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)

    return {
        "ok": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": backend,
        "n_qubits": n,
        "n_layers": n_layers,
        "n_params": n_params,
        "n_evals": n_evals,
        "seed": seed,
        "mean_elapsed_ms": round(float(np.mean(times)), 2),
        "min_elapsed_ms": round(float(np.min(times)), 2),
        "max_elapsed_ms": round(float(np.max(times)), 2),
        "expectation_values": [float(x) for x in np.asarray(result).ravel()],
    }


def main():
    parser = argparse.ArgumentParser(
        description="GPU vs CPU PennyLane simulation benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=6, help="Number of qubits / assets")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--backend", type=str, default="default.qubit",
                        help="PennyLane device (default.qubit | lightning.gpu | lightning.qubit)")
    parser.add_argument("--n-layers", type=int, default=2, help="VQE circuit depth")
    parser.add_argument("--n-evals", type=int, default=5, help="Number of circuit evaluations to time")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print(f"GPU Simulation Benchmark  backend={args.backend}  n={args.n}")
    print("=" * 60)

    result = run_benchmark(args.n, args.backend, args.seed, args.n_layers, args.n_evals)

    if result["ok"]:
        print(f"  Backend      : {result['backend']}")
        print(f"  Qubits       : {result['n_qubits']}")
        print(f"  Layers       : {result['n_layers']}")
        print(f"  Mean elapsed : {result['mean_elapsed_ms']} ms")
        print(f"  Min elapsed  : {result['min_elapsed_ms']} ms")
        print(f"  Status       : PASS")
    else:
        print(f"  Backend      : {result['backend']}")
        print(f"  Error        : {result['error']}")
        print(f"  Status       : FAIL")

    text = json.dumps(result, indent=2)
    print("\n=== Artifact ===")
    print(text)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"\nArtifact saved to: {path.resolve()}")

    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
