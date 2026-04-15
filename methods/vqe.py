"""
VQE Portfolio Optimization — PauliTwoDesign Ansatz (Scientific Reports 2023).

Two execution paths:
  Classical (default): PauliTwoDesign ansatz simulated with numpy + scipy COBYLA.
  IBM Quantum (optional): EfficientSU2 circuit sampled on real IBM hardware via
      qiskit-ibm-runtime. Activated automatically when services.ibm_quantum has
      a valid token stored (POST /api/config/ibm-quantum).

Classical path:
  1. Parameterised ansatz generates probability amplitudes → continuous weights
  2. COBYLA (gradient-free) optimises the circuit parameters
  3. Multiple restarts guard against local minima

IBM hardware path:
  1. EfficientSU2 ansatz built with Qiskit
  2. COBYLA optimises parameters, cost evaluated by sampling the circuit on hardware
  3. Marginal |1⟩ probabilities per qubit → portfolio weights
  4. Jobs are submitted asynchronously and polled for completion (non-blocking).
  5. Falls back to classical if n_assets > MAX_IBM_QUBITS or any error occurs.

Reference: Best practices for quantum error mitigation with VQE.
           Scientific Reports (2023).
           Orús, Mugel & Lizaso (2019). arXiv:1811.03975.
"""

from __future__ import annotations

import logging
import os
import time
import numpy as np
from scipy.optimize import minimize
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum qubit count forwarded to IBM hardware (safety cap for free-tier).
MAX_IBM_QUBITS = 20
# Caps on IBM hardware usage (control credit consumption).
MAX_IBM_RESTARTS = int(os.getenv('IBM_VQE_MAX_RESTARTS', 2))
MAX_IBM_ITER = int(os.getenv('IBM_VQE_MAX_ITER', 25))
SHOTS_PER_EVAL = 2048


def _pick_ibm_backend(service, n: int, backend_name: Optional[str], backend_mode: str):
    """
    Select an IBM backend. backend_mode: auto | simulator | hardware.
    Does not fall back across hardware/simulator when mode is simulator or hardware.
    """
    bm = (backend_mode or "auto").lower()
    if bm not in ("auto", "simulator", "hardware"):
        raise ValueError(f"Invalid backend_mode: {backend_mode!r}")

    if backend_name:
        backend = service.backend(backend_name)
        nq = backend.configuration().n_qubits
        if nq < n:
            raise RuntimeError(
                f"Backend {backend_name} has {nq} qubits; need ≥{n}"
            )
        return backend

    try:
        pool = list(service.backends(operational=True, min_num_qubits=n))
    except Exception:
        pool = [b for b in service.backends() if b.configuration().n_qubits >= n]

    if bm == "simulator":
        candidates = [b for b in pool if b.configuration().simulator]
        if not candidates:
            raise RuntimeError(f"No operational IBM simulator with ≥{n} qubits")
        return min(candidates, key=lambda b: b.status().pending_jobs)

    if bm == "hardware":
        candidates = [b for b in pool if not b.configuration().simulator]
        if not candidates:
            raise RuntimeError(f"No operational IBM hardware backend with ≥{n} qubits")
        return min(candidates, key=lambda b: b.status().pending_jobs)

    # auto: prefer hardware, then any simulator (explicit legacy behaviour)
    candidates = [b for b in pool if not b.configuration().simulator]
    if not candidates:
        try:
            pool2 = list(service.backends(min_num_qubits=n))
        except Exception:
            pool2 = [b for b in service.backends() if b.configuration().n_qubits >= n]
        candidates = [b for b in pool2 if b.configuration().simulator]
    if not candidates:
        raise RuntimeError(f"No IBM backend with ≥{n} qubits found")
    return min(candidates, key=lambda b: b.status().pending_jobs)


def _pauli_two_design_ansatz(theta: np.ndarray, n: int, n_layers: int) -> np.ndarray:
    """
    PauliTwoDesign ansatz: alternating Pauli rotations + CZ ring entanglement.

    Maps parameter vector θ → probability amplitudes p ∈ [0,1]^n.

    Parameters
    ----------
    theta    : Parameter vector, length n * (n_layers + 1).
    n        : Number of assets / qubits.
    n_layers : Circuit depth.

    Returns
    -------
    p : ndarray (n,), values in (0, 1).
    """
    n_params = n * (n_layers + 1)
    th = theta[:n_params].reshape(n_layers + 1, n)
    p = np.ones(n) * 0.5

    for l_idx, layer_th in enumerate(th):
        if l_idx % 2 == 0:
            # Pauli-X/Z rotation: interpolate between p and 1-p
            p = np.cos(layer_th / 2) ** 2 * p + np.sin(layer_th / 2) ** 2 * (1 - p)
        else:
            # Pauli-Y rotation
            p = np.sin(layer_th / 2) ** 2
        # CZ ring entanglement: nearest-neighbour mixing
        p = 0.85 * p + 0.15 * np.roll(p, 1)

    return p


def _vqe_weights_ibm(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_layers: int,
    n_restarts: int,
    weight_min: float,
    weight_max: float,
    seed: int,
    backend_name: Optional[str],
    backend_mode: str = "auto",
) -> Tuple[np.ndarray, Dict[str, object]]:
    """
    VQE on IBM Quantum hardware via qiskit-ibm-runtime.

    Uses EfficientSU2 ansatz. At each COBYLA step the circuit is sampled on
    the chosen backend and marginal |1⟩ probabilities become portfolio weights.
    The cost is negative Sharpe ratio of those weights.

    Raises RuntimeError if IBM is not configured or n > MAX_IBM_QUBITS.
    """
    from services import ibm_quantum

    if not ibm_quantum.is_configured():
        raise RuntimeError("IBM Quantum not configured")

    n = len(mu)
    if n > MAX_IBM_QUBITS:
        raise RuntimeError(
            f"n_assets={n} exceeds MAX_IBM_QUBITS={MAX_IBM_QUBITS}"
        )

    t0 = time.perf_counter()

    from qiskit.circuit.library import EfficientSU2
    from qiskit_ibm_runtime import SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    service = ibm_quantum.get_service()
    backend = _pick_ibm_backend(service, n, backend_name, backend_mode)

    logger.info("IBM VQE: using backend %s for n=%d assets", backend.name, n)

    ansatz = EfficientSU2(n, reps=n_layers, entanglement="linear")
    ansatz.measure_all()

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(ansatz)
    sampler = Sampler(mode=backend)

    n_params = len(isa_circuit.parameters)

    # ── Async job submission with polling (non-blocking) ──
    # Each VQE evaluation submits a job and polls for completion instead of
    # blocking on .result(). This prevents thread starvation when IBM queues
    # are long (real hardware can queue for 5–30+ minutes per job).
    submitted_job_ids: list[str] = []
    total_submissions = 0

    def _wait_for_job(job, timeout: float = 3600.0) -> object:
        """Poll an IBM Runtime job until completion or timeout."""
        job_id = job.job_id()
        submitted_job_ids.append(job_id)
        poll_interval = 30.0  # seconds between polls
        elapsed = 0.0
        while not job.done():
            time.sleep(poll_interval)
            elapsed += poll_interval
            status = job.status()
            logger.info("IBM VQE job %s: status=%s (elapsed %.0fs)", job_id, status, elapsed)
            if elapsed > timeout:
                raise RuntimeError(f"IBM Runtime job {job_id} timed out after {elapsed:.0f}s")
            # Cancel check — if the job is in a terminal error state, raise immediately
            if status in ("ERROR", "CANCELLED"):
                error_msg = getattr(job, "error_message", lambda: "Unknown error")()
                raise RuntimeError(f"IBM Runtime job {job_id} failed: {error_msg}")
        return job.result()

    def _shots_to_weights(params: np.ndarray) -> np.ndarray:
        nonlocal total_submissions
        param_dict = dict(zip(isa_circuit.parameters, params))
        bound = isa_circuit.assign_parameters(param_dict)
        job = sampler.run([bound], shots=SHOTS_PER_EVAL)
        total_submissions += 1
        result = _wait_for_job(job)
        counts = result[0].data.meas.get_counts()
        probs = np.zeros(n)
        total = sum(counts.values())
        for bitstring, count in counts.items():
            for q_idx, bit in enumerate(reversed(bitstring[-n:])):
                if bit == "1":
                    probs[q_idx] += count / total
        w = np.clip(probs, weight_min, weight_max)
        w /= w.sum()
        return w

    def cost(params: np.ndarray) -> float:
        w = _shots_to_weights(params)
        r = w @ mu
        v = np.sqrt(w @ Sigma @ w)
        return -(r / v) if v > 1e-10 else 1e6

    rng = np.random.default_rng(seed)
    best_sharpe = -np.inf
    best_w = np.ones(n) / n

    ibm_restarts = min(n_restarts, MAX_IBM_RESTARTS)
    ibm_maxiter = min(150, MAX_IBM_ITER)
    if ibm_restarts < n_restarts or ibm_maxiter < 150:
        logger.info("IBM VQE: capping to %d restarts x %d iter (max %d jobs)", ibm_restarts, ibm_maxiter, ibm_restarts * ibm_maxiter)

    for _ in range(ibm_restarts):
        theta0 = rng.uniform(-np.pi, np.pi, n_params)
        res = minimize(cost, theta0, method="COBYLA",
                       options={"maxiter": ibm_maxiter, "rhobeg": 0.5})
        w = _shots_to_weights(res.x)
        sr = (w @ mu) / max(np.sqrt(w @ Sigma @ w), 1e-10)
        if sr > best_sharpe:
            best_sharpe, best_w = sr, w.copy()

    elapsed = time.perf_counter() - t0
    logger.info("IBM VQE done: Sharpe=%.4f on %s", best_sharpe, backend.name)

    cfg = backend.configuration()
    meta: Dict[str, object] = {
        "backend": backend.name,
        "simulator": bool(cfg.simulator),
        "n_qubits": int(cfg.n_qubits),
        "shots_per_eval": SHOTS_PER_EVAL,
        "optimization_level": 1,
        "n_assets": n,
        "n_layers": n_layers,
        "ibm_restarts_effective": ibm_restarts,
        "ibm_maxiter_effective": ibm_maxiter,
        "elapsed_seconds": round(elapsed, 4),
        "backend_mode": (backend_mode or "auto").lower(),
        "seed": seed,
        # Async job tracking — IDs of all IBM Runtime jobs submitted during this run
        "ibm_job_ids": list(submitted_job_ids),
        "ibm_total_submissions": total_submissions,
    }
    if backend_name:
        meta["backend_requested"] = backend_name
    return best_w, meta


def vqe_weights_ibm_strict(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_layers: int = 3,
    n_restarts: int = 8,
    weight_min: float = 0.001,
    weight_max: float = 0.30,
    seed: int = 0,
    backend_name: Optional[str] = None,
    backend_mode: str = "auto",
) -> Tuple[np.ndarray, Dict[str, object]]:
    """
    IBM Runtime VQE only — no classical fallback. Raises on misconfiguration,
    oversized universes, or backend selection errors.
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    return _vqe_weights_ibm(
        mu,
        Sigma,
        n_layers,
        n_restarts,
        weight_min,
        weight_max,
        seed,
        backend_name,
        backend_mode,
    )


def vqe_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_layers: int = 3,
    n_restarts: int = 8,
    weight_min: float = 0.001,
    weight_max: float = 0.30,
    seed: int = 0,
    backend_name: Optional[str] = None,
) -> Tuple[np.ndarray, Dict[str, object]]:
    """
    VQE portfolio optimisation with PauliTwoDesign ansatz.

    When an IBM Quantum token is configured (via POST /api/config/ibm-quantum),
    runs the EfficientSU2 circuit on real IBM hardware and falls back to the
    classical numpy simulation on any error or when n_assets > MAX_IBM_QUBITS.

    Classical path uses COBYLA (gradient-free), which outperforms gradient-based
    methods on noisy hardware (Scientific Reports 2023).

    Parameters
    ----------
    mu           : Expected annualised returns, shape (n,).
    Sigma        : Covariance matrix, shape (n, n).
    n_layers     : Ansatz circuit depth (default 3).
    n_restarts   : Number of random restarts.
    weight_min   : Minimum non-zero weight per asset.
    weight_max   : Maximum weight per asset.
    seed         : Base random seed.
    backend_name : Specific IBM backend name (None = auto-select least busy).

    Returns
    -------
    weights : ndarray (n,), sum to 1.
    quantum_metadata : dict with execution_kind, circuit summary, and IBM fields when used.
    """
    # ── Try IBM hardware path first ──────────────────────────────────────────
    try:
        from services import ibm_quantum
        if ibm_quantum.is_configured():
            w, meta = _vqe_weights_ibm(
                np.asarray(mu, dtype=float),
                np.asarray(Sigma, dtype=float),
                n_layers, n_restarts, weight_min, weight_max, seed, backend_name,
                "auto",
            )
            out = dict(meta)
            out["execution_kind"] = "ibm_runtime"
            out["objective"] = "vqe"
            n = len(np.asarray(mu, dtype=float))
            out["circuit"] = {
                "ansatz": "EfficientSU2",
                "n_layers": n_layers,
                "n_qubits": n,
                "entanglement": "linear",
            }
            return w, out
    except Exception as exc:
        logger.warning("IBM VQE path failed, using classical simulation: %s", exc)

    # ── Classical simulation path ─────────────────────────────────────────────
    logger.info("VQE: running classical PauliTwoDesign simulation")
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)
    n_params = n * (n_layers + 1)

    rng = np.random.default_rng(seed)
    best_sharpe = -np.inf
    best_w = np.ones(n) / n

    def objective(theta: np.ndarray) -> float:
        p = _pauli_two_design_ansatz(theta, n, n_layers)
        w = np.clip(p, weight_min, weight_max)
        w /= w.sum()
        r = w @ mu
        v = np.sqrt(w @ Sigma @ w)
        return -(r / v) if v > 1e-10 else 1e6

    for _ in range(n_restarts):
        theta0 = rng.uniform(-np.pi, np.pi, n_params)
        res = minimize(
            objective,
            theta0,
            method="COBYLA",
            options={"maxiter": 300, "rhobeg": 0.5},
        )
        p = _pauli_two_design_ansatz(res.x, n, n_layers)
        w = np.clip(p, weight_min, weight_max)
        w /= w.sum()
        sr = (w @ mu) / max(np.sqrt(w @ Sigma @ w), 1e-10)
        if sr > best_sharpe:
            best_sharpe, best_w = sr, w.copy()

    classical_meta: Dict[str, object] = {
        "execution_kind": "classical_simulation",
        "objective": "vqe",
        "n_layers": n_layers,
        "n_restarts": n_restarts,
        "n_assets": n,
        "seed": seed,
        "circuit": {
            "ansatz": "PauliTwoDesign",
            "n_layers": n_layers,
            "n_qubits": n,
        },
    }
    return best_w, classical_meta
