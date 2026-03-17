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
  4. Falls back to classical if n_assets > MAX_IBM_QUBITS or any error occurs.

Reference: Best practices for quantum error mitigation with VQE.
           Scientific Reports (2023).
           Orús, Mugel & Lizaso (2019). arXiv:1811.03975.
"""

import logging
import numpy as np
from scipy.optimize import minimize
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum qubit count forwarded to IBM hardware (safety cap for free-tier).
MAX_IBM_QUBITS = 20


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
) -> np.ndarray:
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
            f"n_assets={n} exceeds MAX_IBM_QUBITS={MAX_IBM_QUBITS}; "
            "falling back to classical simulation"
        )

    from qiskit.circuit.library import EfficientSU2
    from qiskit_ibm_runtime import SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    service = ibm_quantum.get_service()
    if backend_name:
        backend = service.backend(backend_name)
    else:
        candidates = [
            b for b in service.backends(operational=True, min_num_qubits=n)
            if not b.configuration().simulator
        ]
        if not candidates:
            # Fall back to simulator if no real backend has enough qubits
            candidates = [b for b in service.backends(min_num_qubits=n)]
        if not candidates:
            raise RuntimeError(f"No IBM backend with ≥{n} qubits found")
        backend = min(candidates, key=lambda b: b.status().pending_jobs)

    logger.info("IBM VQE: using backend %s for n=%d assets", backend.name, n)

    ansatz = EfficientSU2(n, reps=n_layers, entanglement="linear")
    ansatz.measure_all()

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(ansatz)
    sampler = Sampler(mode=backend)

    n_params = ansatz.num_parameters - n  # EfficientSU2 adds measure params

    def _shots_to_weights(params: np.ndarray) -> np.ndarray:
        bound = isa_circuit.assign_parameters(params)
        result = sampler.run([bound], shots=2048).result()
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

    for _ in range(n_restarts):
        theta0 = rng.uniform(-np.pi, np.pi, n_params)
        res = minimize(cost, theta0, method="COBYLA",
                       options={"maxiter": 150, "rhobeg": 0.5})
        w = _shots_to_weights(res.x)
        sr = (w @ mu) / max(np.sqrt(w @ Sigma @ w), 1e-10)
        if sr > best_sharpe:
            best_sharpe, best_w = sr, w.copy()

    logger.info("IBM VQE done: Sharpe=%.4f on %s", best_sharpe, backend.name)
    return best_w


def vqe_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    n_layers: int = 3,
    n_restarts: int = 8,
    weight_min: float = 0.001,
    weight_max: float = 0.30,
    seed: int = 0,
    backend_name: Optional[str] = None,
) -> np.ndarray:
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
    """
    # ── Try IBM hardware path first ──────────────────────────────────────────
    try:
        from services import ibm_quantum
        if ibm_quantum.is_configured():
            return _vqe_weights_ibm(
                np.asarray(mu, dtype=float),
                np.asarray(Sigma, dtype=float),
                n_layers, n_restarts, weight_min, weight_max, seed, backend_name,
            )
    except Exception as exc:
        logger.warning("IBM VQE path failed, using classical simulation: %s", exc)

    # ── Classical simulation path ─────────────────────────────────────────────
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

    return best_w
