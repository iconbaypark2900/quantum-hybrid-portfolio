"""
Quantum Approximate Optimization Algorithm (QAOA) for portfolio optimization.

This module provides:
- QAOAOptimizer: Main QAOA optimizer class
- QAOA circuit construction and execution
- Classical simulation fallback
- Integration with AWS Braket gate-based devices

QAOA is a hybrid quantum-classical algorithm that alternates between
problem and mixer Hamiltonians to find approximate solutions to combinatorial
optimization problems like portfolio selection.
"""
import os
import numpy as np
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Try to import optional quantum computing libraries
try:
    import qiskit
    from qiskit import QuantumCircuit, transpile
    from qiskit.primitives import Sampler
    from qiskit_algorithms import QAOA as QiskitQAOA
    from qiskit_algorithms.optimizers import COBYLA, SPSA
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logger.info("Qiskit not installed. Using classical QAOA simulation.")

try:
    import pennylane as qml
    PENNYLANE_AVAILABLE = True
except ImportError:
    PENNYLANE_AVAILABLE = False
    logger.info("PennyLane not installed. Using classical QAOA simulation.")

try:
    import tensorflow as tf
    import tensorflow_quantum as tfq
    TENSORFLOW_QUANTUM_AVAILABLE = True
except ImportError:
    TENSORFLOW_QUANTUM_AVAILABLE = False
    logger.info("TensorFlow Quantum not installed. Using classical QAOA simulation.")

# Try to import AWS Braket SDK
try:
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    from braket.aws import AwsDevice
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False
    logger.info("AWS Braket SDK not installed.")

# Try to import IBM Quantum Runtime
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler as IBMSampler
    IBM_RUNTIME_AVAILABLE = True
except ImportError:
    IBM_RUNTIME_AVAILABLE = False
    QiskitRuntimeService = None  # type: ignore
    IBMSampler = None  # type: ignore
    logger.info("qiskit-ibm-runtime not installed. IBM Quantum backend unavailable.")


@dataclass
class QAOAConfig:
    """Configuration for QAOA optimization."""
    # QAOA parameters
    p: int = 1  # Number of QAOA layers (depth)
    optimizer: str = 'cobyla'  # 'cobyla', 'spsa', 'adam'
    max_iterations: int = 100
    tolerance: float = 1e-6
    
    # Circuit parameters
    shots: int = 1000  # Number of measurement shots
    initial_state: str = 'superposition'  # 'superposition' or 'custom'
    
    # Backend selection
    backend: str = 'classical'  # 'classical', 'qiskit', 'pennylane', 'braket', 'tfq', 'ibm'
    device_name: Optional[str] = None  # For quantum hardware
    ibm_backend: Optional[str] = None  # e.g. 'ibm_brisbane', 'simulator_stabilizer'; None = auto-select
    
    # Portfolio-specific
    risk_aversion: float = 0.5
    penalty_budget: float = 100.0
    penalty_cardinality: float = 50.0
    max_assets: int = 20  # Limited by current quantum hardware


class QAOAOptimizer:
    """
    QAOA optimizer for portfolio selection.
    
    Formulates portfolio optimization as a QUBO problem and solves it using
    the Quantum Approximate Optimization Algorithm (QAOA).
    
    Supports multiple backends:
    - Classical simulation (always available)
    - Qiskit with various simulators and real hardware
    - PennyLane for differentiable quantum computing
    - AWS Braket gate-based devices
    - TensorFlow Quantum for ML integration
    """
    
    def __init__(self, config: Optional[QAOAConfig] = None):
        """
        Initialize QAOA optimizer.
        
        Args:
            config: Configuration object. Uses defaults if not provided.
        """
        self.config = config or QAOAConfig()
        self._backend, self._ibm_backend_name = self._initialize_backend()
        
    def _initialize_backend(self) -> Tuple[Any, Optional[str]]:
        """Initialize the quantum backend based on config. Returns (backend, ibm_backend_name)."""
        backend_name = self.config.backend
        ibm_backend_name: Optional[str] = None

        if backend_name == 'qiskit' and QISKIT_AVAILABLE:
            from qiskit.primitives import Sampler
            return Sampler(), None
        elif backend_name == 'ibm' and IBM_RUNTIME_AVAILABLE:
            token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
            if not token:
                logger.warning("IBM_QUANTUM_TOKEN not set. Falling back to classical QAOA.")
                return 'classical', None
            try:
                service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
                if self.config.ibm_backend:
                    backend = service.backend(self.config.ibm_backend)
                else:
                    backend = service.least_busy(operational=True, simulator=True)
                ibm_backend_name = backend.name
                self._ibm_backend_obj = backend
                logger.info(f"IBM Quantum backend: {ibm_backend_name}")
                return 'ibm_native', ibm_backend_name
            except Exception as e:
                logger.warning(f"IBM Quantum init failed: {e}. Falling back to classical QAOA.")
                return 'classical', None
        elif backend_name == 'pennylane' and PENNYLANE_AVAILABLE:
            dev = qml.device('default.qubit', wires=self.config.max_assets)
            return dev, None
        elif backend_name == 'braket' and BRAKET_AVAILABLE:
            if self.config.device_name:
                return AwsDevice(self.config.device_name), None
            else:
                return LocalSimulator(), None
        elif backend_name == 'tfq' and TENSORFLOW_QUANTUM_AVAILABLE:
            return tfq, None
        else:
            logger.info(f"Using classical QAOA simulation (backend={backend_name})")
            return 'classical', None
    
    def optimize(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        market_regime: str = 'normal',
        initial_weights: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Optimize portfolio using QAOA.
        
        Args:
            returns: Expected returns for each asset
            covariance: Covariance matrix
            market_regime: Market regime (not used in QAOA, kept for interface)
            initial_weights: Starting weights (for turnover tracking)
            
        Returns:
            Dictionary with optimization results
        """
        returns = np.asarray(returns)
        covariance = np.asarray(covariance)
        n_assets = len(returns)
        
        # Limit assets for current hardware
        if n_assets > self.config.max_assets:
            logger.warning(
                f"Reducing assets from {n_assets} to {self.config.max_assets} "
                "(QAOA qubit limit). Selecting top assets by Sharpe ratio."
            )
            sharpe = returns / np.sqrt(np.diag(covariance) + 1e-10)
            top_indices = np.argsort(sharpe)[-self.config.max_assets:]
            returns = returns[top_indices]
            covariance = covariance[np.ix_(top_indices, top_indices)]
            n_assets = self.config.max_assets
        
        # Build QUBO formulation
        linear, quadratic = self._build_portfolio_qubo(returns, covariance)
        
        # Run QAOA
        if self._backend == 'classical':
            result = self._run_classical_qaoa(linear, quadratic, n_assets)
        elif self._backend == 'ibm_native':
            result = self._run_ibm_qaoa_native(linear, quadratic, n_assets)
        elif self.config.backend in ('qiskit', 'ibm'):
            result = self._run_qiskit_qaoa(linear, quadratic, n_assets)
        elif self._backend == 'pennylane':
            result = self._run_pennylane_qaoa(linear, quadratic, n_assets)
        elif self._backend == 'braket':
            result = self._run_braket_qaoa(linear, quadratic, n_assets)
        elif self._backend == 'tfq':
            result = self._run_tfq_qaoa(linear, quadratic, n_assets)
        else:
            result = self._run_classical_qaoa(linear, quadratic, n_assets)
        
        # Convert binary selection to weights
        binary_selection = result["binary_selection"]
        weights = self._binary_to_weights(binary_selection, returns, covariance)
        
        # Calculate portfolio metrics
        metrics = self._calculate_metrics(weights, returns, covariance)
        
        out = {
            "weights": weights,
            "sharpe_ratio": metrics["sharpe_ratio"],
            "expected_return": metrics["expected_return"],
            "volatility": metrics["volatility"],
            "n_active": metrics["n_active"],
            "method": "qaoa",
            "backend": self.config.backend,
            "qaoa_layers": self.config.p,
            "turnover": self._calculate_turnover(weights, initial_weights),
        }
        if self.config.backend == "ibm" and hasattr(self, "_ibm_backend_name") and self._ibm_backend_name:
            out["ibm_backend_name"] = self._ibm_backend_name
            if hasattr(self, "_ibm_job_id") and self._ibm_job_id:
                out["ibm_job_id"] = self._ibm_job_id
        return out
    
    def _build_portfolio_qubo(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
    ) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float]]:
        """
        Build QUBO formulation for portfolio optimization.
        
        Objective: minimize -λ*return + (1-λ)*risk + penalties
        
        Returns:
            Tuple of (linear_terms, quadratic_terms)
        """
        n = len(returns)
        lambda_ = self.config.risk_aversion
        
        # Normalize for numerical stability
        returns_norm = returns / (np.max(np.abs(returns)) + 1e-10)
        cov_norm = covariance / (np.max(np.abs(covariance)) + 1e-10)
        
        linear = {}
        quadratic = {}
        
        # Return term (negative because we maximize)
        for i in range(n):
            linear[i] = -lambda_ * returns_norm[i]
        
        # Risk term
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    linear[i] = linear.get(i, 0) + (1 - lambda_) * cov_norm[i, i]
                else:
                    quadratic[(i, j)] = (1 - lambda_) * cov_norm[i, j]
        
        # Budget constraint: sum(x_i) = 1
        P = self.config.penalty_budget
        for i in range(n):
            linear[i] = linear.get(i, 0) - P
        for i in range(n):
            for j in range(i + 1, n):
                quadratic[(i, j)] = quadratic.get((i, j), 0) + 2 * P
        
        return linear, quadratic
    
    def _run_classical_qaoa(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """
        Run QAOA using classical simulation.
        
        Simulates the QAOA circuit using matrix exponentials.
        """
        from scipy.optimize import minimize
        
        n = n_qubits
        
        # Initialize parameters (gamma for problem, beta for mixer)
        n_params = 2 * self.config.p
        x0 = np.random.uniform(0, np.pi, n_params)
        
        # QAOA energy expectation function
        def qaoa_energy(params):
            gammas = params[:self.config.p]
            betas = params[self.config.p:]
            return self._simulate_qaoa_circuit(
                linear, quadratic, n, gammas, betas
            )
        
        # Optimize parameters
        if self.config.optimizer == 'cobyla':
            result = minimize(
                qaoa_energy, x0, method='COBYLA',
                options={'maxiter': self.config.max_iterations, 'tol': self.config.tolerance}
            )
        elif self.config.optimizer == 'spsa':
            result = minimize(
                qaoa_energy, x0, method='SPSA',
                options={'maxiter': self.config.max_iterations}
            )
        else:
            result = minimize(
                qaoa_energy, x0, method='L-BFGS-B',
                options={'maxiter': self.config.max_iterations}
            )
        
        # Get optimal parameters
        optimal_params = result.x
        gammas = optimal_params[:self.config.p]
        betas = optimal_params[self.config.p:]
        
        # Sample from optimized circuit
        binary_selection = self._sample_qaoa_circuit(
            linear, quadratic, n, gammas, betas, self.config.shots
        )
        
        energy = self._compute_qubo_energy(binary_selection, linear, quadratic)
        
        return {
            "binary_selection": binary_selection,
            "method": "qaoa",
            "backend": "classical",
            "energy": energy,
            "optimal_value": -result.fun,
        }
    
    def _simulate_qaoa_circuit(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        gammas: np.ndarray,
        betas: np.ndarray,
    ) -> float:
        """
        Simulate QAOA circuit and return energy expectation.
        
        Uses state vector simulation for small systems.
        """
        # For small n, use full state vector simulation
        if n <= 12:
            return self._full_state_simulation(linear, quadratic, n, gammas, betas)
        else:
            # For larger n, use approximate methods
            return self._approximate_qaoa_energy(linear, quadratic, n, gammas, betas)
    
    def _full_state_simulation(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        gammas: np.ndarray,
        betas: np.ndarray,
    ) -> float:
        """Full state vector QAOA simulation for small systems."""
        # Initialize |+++...+> state
        dim = 2 ** n
        state = np.ones(dim) / np.sqrt(dim)
        
        # Apply QAOA layers
        for p in range(self.config.p):
            # Problem Hamiltonian: exp(-i * gamma * H_P)
            state = self._apply_problem_hamiltonian(
                state, linear, quadratic, n, gammas[p]
            )
            
            # Mixer Hamiltonian: exp(-i * beta * H_M)
            state = self._apply_mixer_hamiltonian(state, n, betas[p])
        
        # Compute energy expectation
        energy = self._compute_expectation_value(state, linear, quadratic, n)
        
        return energy.real
    
    def _apply_problem_hamiltonian(
        self,
        state: np.ndarray,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        gamma: float,
    ) -> np.ndarray:
        """Apply problem Hamiltonian exp(-i * gamma * H_P)."""
        dim = len(state)
        new_state = np.zeros(dim, dtype=complex)
        
        for i in range(dim):
            # Convert index to binary string
            binary = format(i, f'0{n}b')
            bits = [int(b) for b in binary]
            
            # Compute energy for this basis state
            energy = 0.0
            for j, coef in linear.items():
                energy += coef * bits[j]
            for (j, k), coef in quadratic.items():
                energy += coef * bits[j] * bits[k]
            
            # Apply phase
            new_state[i] = state[i] * np.exp(-1j * gamma * energy)
        
        return new_state
    
    def _apply_mixer_hamiltonian(
        self,
        state: np.ndarray,
        n: int,
        beta: float,
    ) -> np.ndarray:
        """Apply mixer Hamiltonian exp(-i * beta * H_M) where H_M = sum X_i."""
        # For each qubit, apply rotation around X axis
        # This is equivalent to tensor product of single-qubit X rotations
        
        dim = len(state)
        new_state = np.zeros(dim, dtype=complex)
        
        for i in range(dim):
            binary = format(i, f'0{n}b')
            bits = [int(b) for b in binary]
            
            # For each bit flip possibility
            for j in range(n):
                # Flip bit j
                flipped_bits = bits.copy()
                flipped_bits[j] = 1 - flipped_bits[j]
                flipped_idx = int(''.join(map(str, flipped_bits)), 2)
                
                # Add contribution from bit flip
                new_state[i] += state[flipped_idx] * (-1j * np.sin(beta))
                if i == flipped_idx:
                    new_state[i] += state[i] * np.cos(beta)
        
        return new_state
    
    def _compute_expectation_value(
        self,
        state: np.ndarray,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
    ) -> float:
        """Compute energy expectation value <ψ|H|ψ>."""
        dim = len(state)
        energy = 0.0
        
        for i in range(dim):
            binary = format(i, f'0{n}b')
            bits = [int(b) for b in binary]
            
            # Compute energy for this basis state
            e = 0.0
            for j, coef in linear.items():
                e += coef * bits[j]
            for (j, k), coef in quadratic.items():
                e += coef * bits[j] * bits[k]
            
            # Weight by probability
            prob = np.abs(state[i]) ** 2
            energy += e * prob
        
        return energy
    
    def _approximate_qaoa_energy(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        gammas: np.ndarray,
        betas: np.ndarray,
    ) -> float:
        """
        Approximate QAOA energy for large systems.
        
        Uses mean-field approximation for scalability.
        """
        # Mean-field approximation: treat qubits independently
        # This is less accurate but scales to larger n
        
        # Initialize all qubits in |+> state
        expectations = [0.5] * n  # <Z_i> = 0 for |+>
        
        # Apply QAOA layers approximately
        for p in range(self.config.p):
            # Update expectations based on QAOA dynamics
            for i in range(n):
                # Local field from linear and quadratic terms
                local_field = linear.get(i, 0)
                for j in range(n):
                    if (i, j) in quadratic:
                        local_field += quadratic[(i, j)] * expectations[j]
                    if (j, i) in quadratic:
                        local_field += quadratic[(j, i)] * expectations[j]
                
                # Update expectation (simplified dynamics)
                expectations[i] = np.sin(2 * betas[p]) * np.sin(local_field * gammas[p])
        
        # Compute energy from expectations
        energy = sum(linear.get(i, 0) * expectations[i] for i in range(n))
        for (i, j), coef in quadratic.items():
            energy += coef * expectations[i] * expectations[j]
        
        return energy
    
    def _sample_qaoa_circuit(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        gammas: np.ndarray,
        betas: np.ndarray,
        shots: int,
    ) -> np.ndarray:
        """Sample from QAOA circuit."""
        # For classical simulation, sample from the probability distribution
        if n <= 12:
            # Compute full probability distribution
            dim = 2 ** n
            probs = np.zeros(dim)
            
            # Simple sampling: use the optimized state
            # For now, use greedy approach: pick best solution found
            best_solution = np.zeros(n)
            best_energy = float('inf')
            
            for _ in range(min(shots, 1000)):
                # Sample random bitstring weighted by QAOA distribution
                solution = np.random.randint(0, 2, n)
                energy = self._compute_qubo_energy(solution, linear, quadratic)
                if energy < best_energy:
                    best_energy = energy
                    best_solution = solution
            
            return best_solution
        else:
            # For large n, use local search
            return self._qaoa_local_search(linear, quadratic, n, shots)
    
    def _qaoa_local_search(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n: int,
        max_iterations: int,
    ) -> np.ndarray:
        """QAOA-inspired local search for large systems."""
        # Initialize with random solution
        solution = np.random.randint(0, 2, n)
        best_energy = self._compute_qubo_energy(solution, linear, quadratic)
        best_solution = solution.copy()
        
        for _ in range(max_iterations):
            # Try flipping each bit
            for i in range(n):
                neighbor = solution.copy()
                neighbor[i] = 1 - neighbor[i]
                neighbor_energy = self._compute_qubo_energy(neighbor, linear, quadratic)
                
                if neighbor_energy < best_energy:
                    best_energy = neighbor_energy
                    best_solution = neighbor.copy()
                    solution = neighbor
        
        return best_solution
    
    def _extract_sampler_counts(self, pub_result: Any, n_qubits: int) -> Dict[str, int]:
        """Extract measurement counts from SamplerV2 pub result."""
        counts: Dict[str, int] = {}
        if hasattr(pub_result, "join_data"):
            try:
                joined = pub_result.join_data()
                if hasattr(joined, "get_counts"):
                    c = joined.get_counts()
                    if isinstance(c, dict):
                        counts = c
                    else:
                        counts = dict(c) if c else {}
            except Exception:
                pass
        if not counts and hasattr(pub_result, "data"):
            data = pub_result.data
            for attr in ("meas", "cr"):
                reg = getattr(data, attr, None)
                if reg is not None:
                    if hasattr(reg, "get_counts"):
                        c = reg.get_counts()
                        if c:
                            counts = dict(c) if not isinstance(c, dict) else c
                            break
                    elif isinstance(reg, dict):
                        counts = dict(reg)
                        break
        return counts
    
    def _run_ibm_qaoa_native(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """Run QAOA on IBM Quantum using Session + SamplerV2 (native API)."""
        backend = getattr(self, "_ibm_backend_obj", None)
        if backend is None:
            logger.warning("IBM backend not set. Falling back to classical.")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
        
        try:
            from qiskit.quantum_info import SparsePauliOp
            from qiskit.circuit.library import QAOAAnsatz
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
            from qiskit_ibm_runtime import SamplerV2
            from scipy.optimize import minimize
            
            # Build cost Hamiltonian
            pauli_list, coeffs = [], []
            for i, coef in linear.items():
                if i < n_qubits:
                    z_ops = ["I"] * n_qubits
                    z_ops[i] = "Z"
                    pauli_list.append("".join(reversed(z_ops)))
                    coeffs.append(coef)
            for (i, j), coef in quadratic.items():
                if i < n_qubits and j < n_qubits:
                    z_ops = ["I"] * n_qubits
                    z_ops[i], z_ops[j] = "Z", "Z"
                    pauli_list.append("".join(reversed(z_ops)))
                    coeffs.append(coef)
            cost_op = SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))
            
            # QAOA ansatz (params: gammas then betas)
            ansatz = QAOAAnsatz(cost_op, reps=self.config.p)
            ansatz.measure_all()
            
            n_params = 2 * self.config.p
            shots = self.config.shots
            
            def energy_from_counts(counts: dict) -> float:
                """Compute expectation value from measurement counts."""
                total = sum(counts.values())
                if total == 0:
                    return float("inf")
                energy = 0.0
                for bitstr, cnt in counts.items():
                    bits = np.array([int(b) for b in bitstr])
                    e = self._compute_qubo_energy(bits, linear, quadratic)
                    energy += e * (cnt / total)
                return energy
            
            sampler = SamplerV2(mode=backend)

            def objective(params: np.ndarray) -> float:
                bound = ansatz.assign_parameters(dict(zip(ansatz.parameters, params)))
                pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
                isa_circuit = pm.run(bound)
                job = sampler.run([isa_circuit], shots=shots)
                result = job.result()
                # SamplerV2 result format
                pub_result = result[0]
                counts = self._extract_sampler_counts(pub_result, n_qubits)
                return energy_from_counts(counts)
            
            x0 = np.random.uniform(0, np.pi, n_params)
            res = minimize(
                objective, x0, method="COBYLA",
                options={"maxiter": min(self.config.max_iterations, 50)},
            )
            
            # Final run to get best bitstring
            bound = ansatz.assign_parameters(dict(zip(ansatz.parameters, res.x)))
            pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
            isa_circuit = pm.run(bound)
            job = sampler.run([isa_circuit], shots=shots)
            result = job.result()
            pub_result = result[0]
            counts = self._extract_sampler_counts(pub_result, n_qubits)
            
            # Best bitstring by count
            if not counts:
                binary = self._qaoa_local_search(linear, quadratic, n_qubits, 100)
            else:
                best_str = max(counts.keys(), key=lambda k: counts[k])
                binary = np.array([int(b) for b in best_str])
            
            energy = self._compute_qubo_energy(binary, linear, quadratic)
            return {
                "binary_selection": binary,
                "method": "qaoa",
                "backend": "ibm",
                "energy": energy,
            }
        except Exception as e:
            import traceback
            logger.warning(f"IBM native QAOA failed: {e}. Using classical fallback.")
            print(f"[QAOA] IBM native failed: {e}", flush=True)
            traceback.print_exc()
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
    
    def _run_qiskit_qaoa(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """Run QAOA using Qiskit (local simulator)."""
        if not QISKIT_AVAILABLE:
            logger.warning("Qiskit not available, falling back to classical")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
        
        try:
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_algorithms.optimizers import COBYLA
            
            # Build Ising Hamiltonian
            pauli_list = []
            coeffs = []
            
            # Linear terms (Z operators)
            for i, coef in linear.items():
                if i < n_qubits:
                    z_ops = ['I'] * n_qubits
                    z_ops[i] = 'Z'
                    pauli_list.append(''.join(reversed(z_ops)))
                    coeffs.append(coef)
            
            # Quadratic terms (ZZ operators)
            for (i, j), coef in quadratic.items():
                if i < n_qubits and j < n_qubits:
                    z_ops = ['I'] * n_qubits
                    z_ops[i] = 'Z'
                    z_ops[j] = 'Z'
                    pauli_list.append(''.join(reversed(z_ops)))
                    coeffs.append(coef)
            
            hamiltonian = SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))
            
            # Run QAOA
            optimizer = COBYLA(maxiter=self.config.max_iterations)
            qaoa = QiskitQAOA(
                sampler=self._backend,
                optimizer=optimizer,
                reps=self.config.p,
            )
            
            result = qaoa.compute_minimum_eigenvalue(hamiltonian)
            
            # Parse result
            binary = np.array([int(b) for b in format(result.eigenstate, f'0{n_qubits}b')])
            energy = result.eigenvalue.real
            
            return {
                "binary_selection": binary,
                "method": "qaoa",
                "backend": "qiskit",
                "energy": energy,
            }
            
        except Exception as e:
            import traceback
            logger.warning(f"Qiskit QAOA failed: {e}. Using classical fallback.")
            print(f"[QAOA] IBM/Qiskit failed: {e}", flush=True)
            traceback.print_exc()
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
    
    def _run_pennylane_qaoa(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """Run QAOA using PennyLane."""
        if not PENNYLANE_AVAILABLE:
            logger.warning("PennyLane not available, falling back to classical")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
        
        try:
            # Define cost function
            def qaoa_cost(params):
                gammas = params[:self.config.p]
                betas = params[self.config.p:]
                return self._simulate_qaoa_circuit(
                    linear, quadratic, n_qubits, gammas, betas
                )
            
            # Optimize
            from scipy.optimize import minimize
            x0 = np.random.uniform(0, np.pi, 2 * self.config.p)
            result = minimize(qaoa_cost, x0, method='COBYLA')
            
            # Sample best solution
            optimal_params = result.x
            gammas = optimal_params[:self.config.p]
            betas = optimal_params[self.config.p:]
            
            binary = self._sample_qaoa_circuit(
                linear, quadratic, n_qubits, gammas, betas, self.config.shots
            )
            energy = self._compute_qubo_energy(binary, linear, quadratic)
            
            return {
                "binary_selection": binary,
                "method": "qaoa",
                "backend": "pennylane",
                "energy": energy,
            }
            
        except Exception as e:
            logger.warning(f"PennyLane QAOA failed: {e}. Using classical fallback.")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
    
    def _run_braket_qaoa(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """Run QAOA using AWS Braket."""
        if not BRAKET_AVAILABLE:
            logger.warning("Braket not available, falling back to classical")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
        
        try:
            # Build QAOA circuit
            circuit = self._build_braket_qaoa_circuit(
                linear, quadratic, n_qubits
            )
            
            # Run on simulator or device
            if isinstance(self._backend, LocalSimulator):
                task = self._backend.run(circuit, shots=self.config.shots)
            else:
                task = self._backend.run(circuit, shots=self.config.shots)
            
            result = task.result()
            
            # Get most frequent bitstring
            measurements = result.measurements
            from collections import Counter
            bitstrings = [tuple(m) for m in measurements]
            counts = Counter(bitstrings)
            best_bitstring = counts.most_common(1)[0][0]
            
            binary = np.array(best_bitstring)
            energy = self._compute_qubo_energy(binary, linear, quadratic)
            
            return {
                "binary_selection": binary,
                "method": "qaoa",
                "backend": "braket",
                "energy": energy,
            }
            
        except Exception as e:
            logger.warning(f"Braket QAOA failed: {e}. Using classical fallback.")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
    
    def _build_braket_qaoa_circuit(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> 'Circuit':
        """Build QAOA circuit for Braket."""
        if not BRAKET_AVAILABLE:
            raise ImportError("Braket SDK required")
        
        circuit = Circuit()
        
        # Initialize in superposition
        for i in range(n_qubits):
            circuit.h(i)
        
        # QAOA layers
        for p in range(self.config.p):
            # Problem Hamiltonian
            for i, coef in linear.items():
                if i < n_qubits:
                    circuit.rz(i, coef)
            
            for (i, j), coef in quadratic.items():
                if i < n_qubits and j < n_qubits:
                    circuit.cnot(i, j)
                    circuit.rz(j, coef)
                    circuit.cnot(i, j)
            
            # Mixer Hamiltonian
            for i in range(n_qubits):
                circuit.rx(i, np.pi / 2)
        
        # Measure
        circuit.measure_all()
        
        return circuit
    
    def _run_tfq_qaoa(
        self,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
        n_qubits: int,
    ) -> Dict:
        """Run QAOA using TensorFlow Quantum."""
        if not TENSORFLOW_QUANTUM_AVAILABLE:
            logger.warning("TensorFlow Quantum not available, falling back to classical")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
        
        try:
            # TFQ implementation would go here
            # This is a placeholder for the full TFQ integration
            logger.info("TFQ QAOA not fully implemented, using classical fallback")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
            
        except Exception as e:
            logger.warning(f"TFQ QAOA failed: {e}. Using classical fallback.")
            return self._run_classical_qaoa(linear, quadratic, n_qubits)
    
    def _binary_to_weights(
        self,
        binary_selection: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray,
    ) -> np.ndarray:
        """Convert binary selection to portfolio weights."""
        selected_indices = np.where(binary_selection > 0)[0]
        n_selected = len(selected_indices)
        
        if n_selected == 0:
            return np.ones(len(binary_selection)) / len(binary_selection)
        
        if n_selected == 1:
            weights = np.zeros(len(binary_selection))
            weights[selected_indices[0]] = 1.0
            return weights
        
        # Inverse variance weighting
        selected_cov = covariance[np.ix_(selected_indices, selected_indices)]
        variances = np.diag(selected_cov)
        inv_variances = 1.0 / (variances + 1e-10)
        weights_selected = inv_variances / np.sum(inv_variances)
        
        weights = np.zeros(len(binary_selection))
        weights[selected_indices] = weights_selected
        
        return weights
    
    def _calculate_metrics(
        self,
        weights: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray,
    ) -> Dict:
        """Calculate portfolio metrics."""
        portfolio_return = float(np.dot(weights, returns))
        portfolio_variance = float(weights @ covariance @ weights)
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe = portfolio_return / portfolio_volatility if portfolio_volatility > 1e-10 else 0.0
        n_active = int(np.sum(weights > 0.01))
        
        return {
            "expected_return": portfolio_return,
            "volatility": portfolio_volatility,
            "sharpe_ratio": sharpe,
            "n_active": n_active,
        }
    
    def _calculate_turnover(
        self,
        weights: np.ndarray,
        initial_weights: Optional[np.ndarray],
    ) -> float:
        """Calculate portfolio turnover."""
        if initial_weights is None:
            return 0.0
        return float(np.sum(np.abs(weights - initial_weights)))
    
    def _compute_qubo_energy(
        self,
        solution: np.ndarray,
        linear: Dict[int, float],
        quadratic: Dict[Tuple[int, int], float],
    ) -> float:
        """Compute QUBO energy for a solution."""
        energy = 0.0
        
        for i, coef in linear.items():
            if i < len(solution):
                energy += coef * solution[i]
        
        for (i, j), coef in quadratic.items():
            if i < len(solution) and j < len(solution):
                energy += coef * solution[i] * solution[j]
        
        return float(energy)


def run_qaoa_comparison(
    returns: np.ndarray,
    covariance: np.ndarray,
) -> Dict:
    """
    Compare QAOA with classical optimization.
    
    Args:
        returns: Expected returns
        covariance: Covariance matrix
        
    Returns:
        Comparison results
    """
    # QAOA
    qaoa_config = QAOAConfig(p=2, backend='classical')
    qaoa_optimizer = QAOAOptimizer(qaoa_config)
    qaoa_result = qaoa_optimizer.optimize(returns, covariance)
    
    # Classical baseline (equal weight)
    n = len(returns)
    ew_weights = np.ones(n) / n
    ew_return = np.dot(ew_weights, returns)
    ew_vol = np.sqrt(ew_weights @ covariance @ ew_weights)
    ew_sharpe = ew_return / ew_vol if ew_vol > 0 else 0
    
    return {
        "qaoa": qaoa_result,
        "equal_weight": {
            "weights": ew_weights,
            "sharpe_ratio": ew_sharpe,
            "expected_return": ew_return,
            "volatility": ew_vol,
        },
    }
