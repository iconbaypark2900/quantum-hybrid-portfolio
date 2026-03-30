"""
QAOA Portfolio Selection — Quantum Approximate Optimization Algorithm.

Solves the same binary asset-selection QUBO as qubo_sa, but replaces
simulated annealing with a parameterised gate-model circuit.

Two execution paths
-------------------
Classical (default):
    Full numpy statevector simulation. Capped at MAX_SIM_QUBITS=12
    assets (statevector grows as 2^n). Safe default — no IBM token needed.

IBM Quantum Runtime:
    Parametrised QAOA circuit transpiled for the chosen backend.
    EstimatorV2 evaluates <H_C> for angle optimisation (COBYLA).
    SamplerV2 samples the final bitstring distribution after convergence.
    Requires a configured IBM token + execution_kind: ibm_runtime in the
    run payload. Capped at MAX_IBM_QUBITS=20.

QUBO → Ising mapping
---------------------
Substitution: x_i = (1 - s_i) / 2  where s_i in {-1, +1} (Z eigenvalue).

  h_i  = -Q[i,i] / 2 - sum_{j!=i} Q[i,j] / 2
  J_ij = Q[i,j] / 2   (for i < j)

QAOA circuit structure (p layers)
----------------------------------
  |psi_0> = H^n |0...0>   (uniform superposition)
  Layer l:
    U_C(gamma_l) = exp(-i gamma_l H_C)   cost unitary
    U_B(beta_l)  = tensor_i Rx(2*beta_l)  mixer unitary
  Optimise (gamma, beta) to minimise <psi|H_C|psi> via COBYLA.
  Extract solution: highest-probability K-cardinality bitstring.

References
----------
Farhi, Goldstone & Gutmann (2014). A Quantum Approximate Optimization
  Algorithm. arXiv:1411.4028.
Zhou et al. (2020). QAOA: Performance, Mechanism, and Implementation on
  NISQ Devices. Phys. Rev. X 10, 021067. arXiv:1812.01041.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from methods.qubo_sa import _build_qubo_matrix
from methods.vqe import MAX_IBM_QUBITS, _pick_ibm_backend

logger = logging.getLogger(__name__)

MAX_SIM_QUBITS: int = 12
MAX_IBM_RESTARTS: int = int(os.getenv("IBM_QAOA_MAX_RESTARTS", 2))
MAX_IBM_ITER: int = int(os.getenv("IBM_QAOA_MAX_ITER", 50))
SHOTS_PER_EVAL: int = 2048

_JDict = Dict[Tuple[int, int], float]


# ── QUBO → Ising ────────────────────────────────────────────────────────────

def _qubo_to_ising(Q: np.ndarray) -> Tuple[np.ndarray, _JDict]:
    """Map symmetric QUBO matrix Q to Ising (h, J) coefficients.

    Returns
    -------
    h : (n,)       single-qubit Z coefficients
    J : {(i,j): v} two-qubit ZZ coefficients for i < j
    """
    n = Q.shape[0]
    row_sums = Q.sum(axis=1)
    h = -Q.diagonal() / 2.0 - (row_sums - Q.diagonal()) / 2.0
    J: _JDict = {
        (i, j): Q[i, j] / 2.0
        for i in range(n)
        for j in range(i + 1, n)
        if abs(Q[i, j]) > 1e-12
    }
    return h, J


# ── Classical statevector helpers ────────────────────────────────────────────

def _cost_energy_diagonal(h: np.ndarray, J: _JDict, n: int) -> np.ndarray:
    """Precompute Ising energy E(z) for every 2^n computational basis state.

    State index s: qubit q has bit value (s >> q) & 1.
    Z eigenvalue: z_q = 1 - 2*bit_q  (+1 for |0>, -1 for |1>).
    """
    idx = np.arange(1 << n)
    bits = (idx[:, None] >> np.arange(n)[None, :]) & 1   # (n_states, n)
    z = 1 - 2 * bits                                       # Z eigenvalues
    diag = z @ h                                           # linear Z terms
    for (i, j), val in J.items():
        diag = diag + val * z[:, i] * z[:, j]             # ZZ terms
    return diag


def _apply_cost_unitary(state: np.ndarray, cost_diag: np.ndarray, gamma: float) -> np.ndarray:
    """Apply U_C(γ) = exp(-i γ H_C) as elementwise phase multiplication."""
    return state * np.exp(-1j * gamma * cost_diag)


def _apply_mixer(state: np.ndarray, n: int, beta: float) -> np.ndarray:
    """Apply U_B(β) = ⊗_i exp(-i β X_i) qubit-by-qubit."""
    cos_b = np.cos(beta)
    sin_b = np.sin(beta)
    for q in range(n):
        s = state.reshape(-1, 2, 1 << q)
        new_s = np.empty_like(s)
        new_s[:, 0, :] = cos_b * s[:, 0, :] - 1j * sin_b * s[:, 1, :]
        new_s[:, 1, :] = -1j * sin_b * s[:, 0, :] + cos_b * s[:, 1, :]
        state = new_s.reshape(-1)
    return state


def _qaoa_statevector(
    n: int,
    p: int,
    gammas: np.ndarray,
    betas: np.ndarray,
    cost_diag: np.ndarray,
) -> np.ndarray:
    """Run p-layer QAOA circuit on a numpy statevector; return final state."""
    state = np.ones(1 << n, dtype=complex) / np.sqrt(1 << n)
    for layer in range(p):
        state = _apply_cost_unitary(state, cost_diag, gammas[layer])
        state = _apply_mixer(state, n, betas[layer])
    return state


def _select_k_from_probs(probs: np.ndarray, K: int, n: int) -> np.ndarray:
    """Return equal-weight portfolio on the highest-probability K-hot bitstring."""
    n_states = 1 << n
    best_prob = -1.0
    best_bits: Optional[list] = None

    for s in range(n_states):
        bits = [(s >> q) & 1 for q in range(n)]
        if sum(bits) == K and probs[s] > best_prob:
            best_prob = probs[s]
            best_bits = bits

    if best_bits is None:
        # No K-cardinality state found — fall back to top-K by probability
        top = np.argsort(probs)[::-1][:K]
        w = np.zeros(n)
        w[top] = 1.0 / K
        return w

    selected = [q for q in range(n) if best_bits[q] == 1]
    w = np.zeros(n)
    if selected:
        w[np.array(selected)] = 1.0 / len(selected)
    return w


# ── Classical public entry point ─────────────────────────────────────────────

def qaoa_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K: Optional[int] = None,
    p: int = 2,
    lambda_risk: float = 1.0,
    gamma: float = 8.0,
    n_restarts: int = 4,
    weight_min: float = 0.005,
    weight_max: float = 0.30,
    seed: int = 42,
) -> np.ndarray:
    """
    QAOA portfolio selection — classical numpy statevector path.

    Parameters
    ----------
    mu          : Expected annualised returns, shape (n,).
    Sigma       : Covariance matrix, shape (n, n).
    K           : Number of assets to select. Defaults to max(2, n // 3).
    p           : QAOA circuit depth (cost + mixer layers).
    lambda_risk : Risk aversion coefficient in QUBO.
    gamma       : Cardinality penalty strength in QUBO.
    n_restarts  : Independent COBYLA restarts.
    weight_min  : Informational lower bound (post-selection equal-weight ignores this).
    weight_max  : Informational upper bound.
    seed        : Random seed.

    Returns
    -------
    weights : ndarray (n,), sums to 1. Selected assets receive equal weight.
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)

    if n > MAX_SIM_QUBITS:
        raise ValueError(
            f"n_assets={n} exceeds MAX_SIM_QUBITS={MAX_SIM_QUBITS} for classical QAOA "
            f"statevector simulation. Use objective='qubo_sa' for larger universes, "
            f"or use execution_kind='ibm_runtime' with a configured IBM token "
            f"(IBM cap: {MAX_IBM_QUBITS} qubits)."
        )

    if K is None:
        K = max(2, n // 3)
    K = min(K, n)

    Q = _build_qubo_matrix(mu, Sigma, K, lambda_risk, gamma)
    h, J = _qubo_to_ising(Q)
    cost_diag = _cost_energy_diagonal(h, J, n)

    rng = np.random.default_rng(seed)
    best_energy = np.inf
    best_params: Optional[np.ndarray] = None

    def _energy(params: np.ndarray) -> float:
        state = _qaoa_statevector(n, p, params[:p], params[p:], cost_diag)
        return float((np.abs(state) ** 2) @ cost_diag)

    for _ in range(n_restarts):
        theta0 = np.concatenate([
            rng.uniform(0.0, np.pi, p),
            rng.uniform(0.0, np.pi / 2, p),
        ])
        res = minimize(_energy, theta0, method="COBYLA",
                       options={"maxiter": 300, "rhobeg": 0.3})
        if res.fun < best_energy:
            best_energy = res.fun
            best_params = res.x

    if best_params is None:
        best_params = rng.uniform(0.0, np.pi, 2 * p)

    final_state = _qaoa_statevector(n, p, best_params[:p], best_params[p:], cost_diag)
    probs = np.abs(final_state) ** 2
    w = _select_k_from_probs(probs, K, n)

    logger.info(
        "qaoa (classical): n=%d K=%d p=%d restarts=%d best_energy=%.4f",
        n, K, p, n_restarts, best_energy,
    )
    return w


# ── Qiskit circuit builder (IBM path) ───────────────────────────────────────

def _build_qaoa_circuit_qiskit(
    n: int, p: int, h: np.ndarray, J: _JDict
):
    """Build a parametrised QAOA QuantumCircuit and SparsePauliOp cost Hamiltonian.

    Returns (circuit, hamiltonian, all_params_ordered).
    all_params_ordered = [gamma_0, ..., gamma_{p-1}, beta_0, ..., beta_{p-1}].
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit import ParameterVector
    from qiskit.quantum_info import SparsePauliOp

    gammas = ParameterVector("γ", p)
    betas = ParameterVector("β", p)
    all_params = list(gammas) + list(betas)

    qc = QuantumCircuit(n)
    qc.h(range(n))  # uniform superposition

    for layer in range(p):
        # Cost unitary: ZZ and Z rotations
        for (i, j), val in J.items():
            qc.rzz(2.0 * val * gammas[layer], i, j)
        for q in range(n):
            if abs(h[q]) > 1e-10:
                qc.rz(2.0 * h[q] * gammas[layer], q)
        # Mixer unitary: Rx on every qubit
        for q in range(n):
            qc.rx(2.0 * betas[layer], q)

    # Build SparsePauliOp (Qiskit convention: q0 = rightmost character)
    pauli_list = []
    for q in range(n):
        if abs(h[q]) > 1e-10:
            op = ["I"] * n
            op[n - 1 - q] = "Z"
            pauli_list.append(("".join(op), h[q]))
    for (i, j), val in J.items():
        if abs(val) > 1e-10:
            op = ["I"] * n
            op[n - 1 - i] = "Z"
            op[n - 1 - j] = "Z"
            pauli_list.append(("".join(op), val))

    if pauli_list:
        hamiltonian = SparsePauliOp.from_list(pauli_list)
    else:
        hamiltonian = SparsePauliOp("I" * n, coeffs=[0.0])

    return qc, hamiltonian, all_params


# ── IBM Quantum Runtime path ─────────────────────────────────────────────────

def _qaoa_weights_ibm(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K: int,
    p: int,
    lambda_risk: float,
    gamma: float,
    n_restarts: int,
    seed: int,
    backend_name: Optional[str],
    backend_mode: str,
) -> Tuple[np.ndarray, Dict]:
    """QAOA on IBM Quantum Runtime (internal implementation).

    EstimatorV2 minimises <H_C> during COBYLA optimisation.
    SamplerV2 samples the final state to extract the bitstring distribution.
    """
    from services import ibm_quantum
    from qiskit_ibm_runtime import EstimatorV2, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    if not ibm_quantum.is_configured():
        raise RuntimeError("IBM Quantum not configured")

    n = len(mu)
    if n > MAX_IBM_QUBITS:
        raise RuntimeError(f"n_assets={n} exceeds MAX_IBM_QUBITS={MAX_IBM_QUBITS}")

    t0 = time.perf_counter()
    service = ibm_quantum.get_service()
    backend = _pick_ibm_backend(service, n, backend_name, backend_mode)
    logger.info("IBM QAOA: backend=%s n=%d p=%d K=%d", backend.name, n, p, K)

    Q = _build_qubo_matrix(mu, Sigma, K, lambda_risk, gamma)
    h_ising, J_ising = _qubo_to_ising(Q)
    qc, hamiltonian, all_params = _build_qaoa_circuit_qiskit(n, p, h_ising, J_ising)

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(qc)
    isa_hamiltonian = hamiltonian.apply_layout(isa_circuit.layout)

    estimator = EstimatorV2(mode=backend)

    ibm_restarts = min(n_restarts, MAX_IBM_RESTARTS)
    ibm_maxiter = min(150, MAX_IBM_ITER)
    rng = np.random.default_rng(seed)
    best_energy = np.inf
    best_angles: Optional[np.ndarray] = None

    def _energy_ibm(params: np.ndarray) -> float:
        param_dict = dict(zip(all_params, params.tolist()))
        bound = isa_circuit.assign_parameters(param_dict)
        result = estimator.run([(bound, isa_hamiltonian)]).result()
        return float(result[0].data.evs)

    for _ in range(ibm_restarts):
        theta0 = np.concatenate([
            rng.uniform(0.0, np.pi, p),
            rng.uniform(0.0, np.pi / 2, p),
        ])
        res = minimize(_energy_ibm, theta0, method="COBYLA",
                       options={"maxiter": ibm_maxiter, "rhobeg": 0.3})
        if res.fun < best_energy:
            best_energy = res.fun
            best_angles = res.x

    if best_angles is None:
        best_angles = rng.uniform(0.0, np.pi, 2 * p)

    # Sample final state to get bitstring probabilities
    qc_meas = qc.copy()
    qc_meas.measure_all()
    isa_meas = pm.run(qc_meas)
    param_dict = dict(zip(all_params, best_angles.tolist()))
    bound_meas = isa_meas.assign_parameters(param_dict)

    sampler = SamplerV2(mode=backend)
    sample_result = sampler.run([bound_meas], shots=SHOTS_PER_EVAL).result()
    counts = sample_result[0].data.meas.get_counts()

    # Build probability array over all 2^n states
    probs = np.zeros(1 << n)
    total = sum(counts.values())
    for bitstring, count in counts.items():
        # Qiskit bitstring: qubit 0 = rightmost character
        trimmed = bitstring[-n:]
        idx = int(trimmed[::-1], 2)   # q0 = bit index 0
        if 0 <= idx < (1 << n):
            probs[idx] += count / total

    w = _select_k_from_probs(probs, K, n)

    elapsed = time.perf_counter() - t0
    cfg = backend.configuration()
    meta: Dict = {
        "backend": backend.name,
        "simulator": bool(cfg.simulator),
        "n_qubits": int(cfg.n_qubits),
        "n_assets": n,
        "p": p,
        "K": K,
        "ibm_restarts_effective": ibm_restarts,
        "ibm_maxiter_effective": ibm_maxiter,
        "best_ising_energy": round(float(best_energy), 6),
        "shots_final": SHOTS_PER_EVAL,
        "elapsed_seconds": round(elapsed, 4),
        "backend_mode": (backend_mode or "auto").lower(),
        "seed": seed,
    }
    if backend_name:
        meta["backend_requested"] = backend_name

    logger.info(
        "IBM QAOA done: energy=%.4f backend=%s elapsed=%.1fs",
        best_energy, backend.name, elapsed,
    )
    return w, meta


def qaoa_weights_ibm_strict(
    mu: np.ndarray,
    Sigma: np.ndarray,
    K: Optional[int] = None,
    p: int = 2,
    lambda_risk: float = 1.0,
    gamma: float = 8.0,
    n_restarts: int = 4,
    seed: int = 0,
    backend_name: Optional[str] = None,
    backend_mode: str = "auto",
) -> Tuple[np.ndarray, Dict]:
    """
    IBM Quantum Runtime QAOA path (public entry point).

    Raises RuntimeError if IBM is not configured or n > MAX_IBM_QUBITS.
    Returns (weights, quantum_metadata).
    """
    mu = np.asarray(mu, dtype=float)
    Sigma = np.asarray(Sigma, dtype=float)
    n = len(mu)
    if K is None:
        K = max(2, n // 3)
    K = min(K, n)

    return _qaoa_weights_ibm(
        mu=mu,
        Sigma=Sigma,
        K=K,
        p=p,
        lambda_risk=lambda_risk,
        gamma=gamma,
        n_restarts=n_restarts,
        seed=seed,
        backend_name=backend_name,
        backend_mode=backend_mode,
    )
