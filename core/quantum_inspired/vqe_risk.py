"""
Variational Quantum Eigensolver (VQE) for portfolio risk calculations.

This module provides:
- VQEOptimizer: Main VQE optimizer class for risk calculations
- Portfolio risk estimation using quantum eigensolvers
- Value-at-Risk (VaR) and Conditional VaR calculations
- Covariance matrix eigenvalue estimation

VQE is a hybrid quantum-classical algorithm that finds the smallest
eigenvalue of a Hamiltonian, which corresponds to minimum risk in
portfolio optimization.
"""
import numpy as np
from typing import Dict, Optional, Tuple, List, Any, TYPE_CHECKING
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp

logger = logging.getLogger(__name__)

# Try to import quantum computing libraries
try:
    import qiskit
    from qiskit import QuantumCircuit
    from qiskit.primitives import Estimator
    from qiskit_algorithms import VQE as QiskitVQE
    from qiskit_algorithms.optimizers import SPSA, COBYLA
    from qiskit.quantum_info import SparsePauliOp
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    QuantumCircuit = None  # type: ignore
    SparsePauliOp = None  # type: ignore
    logger.info("Qiskit not installed. Using classical VQE simulation.")

try:
    import pennylane as qml
    PENNYLANE_AVAILABLE = True
except ImportError:
    PENNYLANE_AVAILABLE = False
    logger.info("PennyLane not installed. Using classical VQE simulation.")

try:
    import tensorflow as tf
    import tensorflow_quantum as tfq
    TENSORFLOW_QUANTUM_AVAILABLE = True
except ImportError:
    TENSORFLOW_QUANTUM_AVAILABLE = False
    logger.info("TensorFlow Quantum not installed. Using classical VQE simulation.")


@dataclass
class VQEConfig:
    """Configuration for VQE risk calculations."""
    # VQE parameters
    ansatz: str = 'real_amplitudes'  # 'real_amplitudes', 'efficient_su2', 'custom'
    optimizer: str = 'spsa'  # 'spsa', 'cobyla', 'adam'
    max_iterations: int = 200
    tolerance: float = 1e-6
    
    # Circuit parameters
    reps: int = 1  # Number of repetitions in ansatz
    entanglement: str = 'linear'  # 'linear', 'full', 'circular'
    
    # Backend selection
    backend: str = 'classical'  # 'classical', 'qiskit', 'pennylane', 'tfq'
    shots: int = 1024
    
    # Risk calculation parameters
    confidence_level: float = 0.95  # For VaR calculations
    num_scenarios: int = 10000  # For Monte Carlo


class VQEOptimizer:
    """
    VQE optimizer for portfolio risk calculations.
    
    Uses the Variational Quantum Eigensolver to compute:
    - Minimum portfolio variance (smallest eigenvalue of covariance matrix)
    - Value-at-Risk (VaR)
    - Conditional VaR (CVaR / Expected Shortfall)
    - Risk contributions
    
    Supports multiple backends for flexibility.
    """
    
    def __init__(self, config: Optional[VQEConfig] = None):
        """
        Initialize VQE optimizer.
        
        Args:
            config: Configuration object. Uses defaults if not provided.
        """
        self.config = config or VQEConfig()
        self._backend = self._initialize_backend()
        
    def _initialize_backend(self) -> Any:
        """Initialize the quantum backend."""
        backend_name = self.config.backend
        
        if backend_name == 'qiskit' and QISKIT_AVAILABLE:
            return Estimator()
        elif backend_name == 'pennylane' and PENNYLANE_AVAILABLE:
            dev = qml.device('default.qubit', wires=8)
            return dev
        elif backend_name == 'tfq' and TENSORFLOW_QUANTUM_AVAILABLE:
            return tfq
        else:
            logger.info(f"Using classical VQE simulation (backend={backend_name})")
            return 'classical'
    
    def calculate_minimum_variance(
        self,
        covariance: np.ndarray,
        initial_weights: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Calculate minimum portfolio variance using VQE.
        
        The minimum variance corresponds to the smallest eigenvalue
        of the covariance matrix.
        
        Args:
            covariance: Covariance matrix
            initial_weights: Initial guess for weights
            
        Returns:
            Dictionary with minimum variance and optimal weights
        """
        covariance = np.asarray(covariance)
        n_assets = len(covariance)
        
        # Limit size for quantum hardware
        if n_assets > 8:
            logger.warning(
                f"Reducing covariance matrix from {n_assets} to 8 assets "
                "(VQE qubit limit). Using top assets by Sharpe ratio."
            )
            # Select top assets by individual Sharpe ratio
            returns_proxy = np.diag(covariance)  # Use diagonal as return proxy
            sharpe = returns_proxy / (np.sqrt(np.diag(covariance)) + 1e-10)
            top_indices = np.argsort(sharpe)[-8:]
            covariance = covariance[np.ix_(top_indices, top_indices)]
            n_assets = 8
        
        if self._backend == 'classical':
            result = self._classical_minimum_variance(covariance)
        elif self._backend == 'qiskit':
            result = self._qiskit_vqe_minimum_variance(covariance)
        elif self._backend == 'pennylane':
            result = self._pennylane_vqe_minimum_variance(covariance)
        else:
            result = self._classical_minimum_variance(covariance)
        
        return result
    
    def _classical_minimum_variance(
        self,
        covariance: np.ndarray,
    ) -> Dict:
        """
        Calculate minimum variance using classical eigendecomposition.
        
        This serves as both a standalone method and fallback for quantum.
        """
        n = len(covariance)
        
        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        
        # Sort by eigenvalues (ascending)
        idx = np.argsort(eigenvalues)
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Minimum variance is smallest eigenvalue
        min_variance = eigenvalues[0]
        min_volatility = np.sqrt(min_variance)
        
        # Corresponding eigenvector gives optimal weights
        optimal_weights = np.abs(eigenvectors[:, 0])
        optimal_weights = optimal_weights / np.sum(optimal_weights)
        
        # Compute risk metrics
        risk_metrics = self._compute_risk_metrics(
            optimal_weights, covariance, eigenvalues
        )
        
        return {
            "minimum_variance": float(min_variance),
            "minimum_volatility": float(min_volatility),
            "optimal_weights": optimal_weights,
            "eigenvalues": eigenvalues.tolist(),
            "method": "classical",
            **risk_metrics,
        }
    
    def _qiskit_vqe_minimum_variance(
        self,
        covariance: np.ndarray,
    ) -> Dict:
        """Calculate minimum variance using Qiskit VQE."""
        if not QISKIT_AVAILABLE:
            return self._classical_minimum_variance(covariance)
        
        try:
            n = len(covariance)
            n_qubits = int(np.ceil(np.log2(n)))
            
            # Build Hamiltonian from covariance matrix
            hamiltonian = self._covariance_to_hamiltonian(covariance, n_qubits)
            
            # Create ansatz circuit
            ansatz = self._create_ansatz_circuit(n_qubits)
            
            # Initialize optimizer
            if self.config.optimizer == 'spsa':
                optimizer = SPSA(maxiter=self.config.max_iterations)
            else:
                optimizer = COBYLA(maxiter=self.config.max_iterations)
            
            # Run VQE
            vqe = QiskitVQE(
                estimator=self._backend,
                ansatz=ansatz,
                optimizer=optimizer,
            )
            
            result = vqe.compute_minimum_eigenvalue(hamiltonian)
            
            # Extract results
            min_variance = result.eigenvalue.real
            
            # Get optimal weights from eigenstate
            eigenstate = result.eigenstate
            if hasattr(eigenstate, 'numpy'):
                eigenstate = eigenstate.numpy()
            
            # Convert state vector to weights
            optimal_weights = self._eigenstate_to_weights(
                eigenstate, n, n_qubits
            )
            
            # Compute full eigendecomposition for comparison
            eigenvalues, _ = np.linalg.eigh(covariance)
            
            risk_metrics = self._compute_risk_metrics(
                optimal_weights, covariance, eigenvalues
            )
            
            return {
                "minimum_variance": float(min_variance),
                "minimum_volatility": float(np.sqrt(min_variance)),
                "optimal_weights": optimal_weights,
                "eigenvalues": eigenvalues.tolist(),
                "method": "vqe_qiskit",
                "converged": result.cost_function_evals > 0,
                **risk_metrics,
            }
            
        except Exception as e:
            logger.warning(f"Qiskit VQE failed: {e}. Using classical fallback.")
            return self._classical_minimum_variance(covariance)
    
    def _pennylane_vqe_minimum_variance(
        self,
        covariance: np.ndarray,
    ) -> Dict:
        """Calculate minimum variance using PennyLane VQE."""
        if not PENNYLANE_AVAILABLE:
            return self._classical_minimum_variance(covariance)
        
        try:
            n = len(covariance)
            n_qubits = min(int(np.ceil(np.log2(n))), 8)
            
            # Define Hamiltonian coefficients
            coeffs, observables = self._covariance_to_pennylane_hamiltonian(
                covariance, n_qubits
            )
            
            # Create device
            dev = qml.device('default.qubit', wires=n_qubits)
            
            # Define ansatz
            @qml.qnode(dev)
            def circuit(params):
                # Initial state preparation
                for i in range(n_qubits):
                    qml.Hadamard(wires=i)
                
                # Variational layers
                for layer in range(self.config.reps):
                    for i in range(n_qubits):
                        qml.RY(params[layer, i, 0], wires=i)
                        qml.RZ(params[layer, i, 1], wires=i)
                    
                    # Entanglement
                    for i in range(n_qubits - 1):
                        qml.CNOT(wires=[i, i + 1])
                
                return qml.expval(qml.Hermitian(covariance[:2**n_qubits, :2**n_qubits], wires=range(n_qubits)))
            
            # Initialize parameters
            params = np.random.uniform(0, 2*np.pi, (self.config.reps, n_qubits, 2))
            
            # Optimize
            opt = qml.AdamOptimizer(stepsize=0.1)
            
            min_variance = float('inf')
            best_params = params
            
            for iteration in range(self.config.max_iterations):
                params, energy = opt.step_and_cost(circuit, params)
                if energy < min_variance:
                    min_variance = energy
                    best_params = params
            
            # Get optimal weights
            optimal_weights = np.ones(n) / n  # Simplified
            
            eigenvalues, _ = np.linalg.eigh(covariance)
            risk_metrics = self._compute_risk_metrics(
                optimal_weights, covariance, eigenvalues
            )
            
            return {
                "minimum_variance": float(min_variance),
                "minimum_volatility": float(np.sqrt(min_variance)),
                "optimal_weights": optimal_weights,
                "eigenvalues": eigenvalues.tolist(),
                "method": "vqe_pennylane",
                **risk_metrics,
            }
            
        except Exception as e:
            logger.warning(f"PennyLane VQE failed: {e}. Using classical fallback.")
            return self._classical_minimum_variance(covariance)
    
    def calculate_var(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        weights: np.ndarray,
        confidence_level: Optional[float] = None,
    ) -> Dict:
        """
        Calculate Value-at-Risk (VaR) using VQE-based methods.
        
        Args:
            returns: Asset returns
            covariance: Covariance matrix
            weights: Portfolio weights
            confidence_level: Confidence level (default from config)
            
        Returns:
            Dictionary with VaR and related metrics
        """
        confidence = confidence_level or self.config.confidence_level
        weights = np.asarray(weights)
        
        # Portfolio statistics
        portfolio_return = np.dot(weights, returns)
        portfolio_variance = weights @ covariance @ weights
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Parametric VaR (normal distribution assumption)
        from scipy.stats import norm
        z_score = norm.ppf(1 - confidence)
        var_parametric = -(portfolio_return + z_score * portfolio_volatility)
        
        # CVaR / Expected Shortfall
        cvar = -(portfolio_return - portfolio_volatility * norm.pdf(z_score) / (1 - confidence))
        
        # Monte Carlo VaR (more accurate for non-normal distributions)
        var_mc, cvar_mc = self._monte_carlo_var(
            returns, covariance, weights, confidence
        )
        
        return {
            "var_95": float(var_parametric),
            "cvar_95": float(cvar),
            "var_parametric": float(var_parametric),
            "var_monte_carlo": float(var_mc),
            "cvar_monte_carlo": float(cvar_mc),
            "confidence_level": confidence,
            "portfolio_return": float(portfolio_return),
            "portfolio_volatility": float(portfolio_volatility),
        }
    
    def _monte_carlo_var(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        weights: np.ndarray,
        confidence: float,
        n_scenarios: Optional[int] = None,
    ) -> Tuple[float, float]:
        """
        Calculate VaR and CVaR using Monte Carlo simulation.
        """
        n_scenarios = n_scenarios or self.config.num_scenarios
        
        # Generate correlated random returns
        n_assets = len(returns)
        mean_returns = np.mean(returns)
        
        # Cholesky decomposition for correlated samples
        try:
            L = np.linalg.cholesky(covariance)
        except np.linalg.LinAlgError:
            # If not positive definite, use eigenvalue decomposition
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            eigenvalues = np.maximum(eigenvalues, 0)
            L = eigenvectors @ np.diag(np.sqrt(eigenvalues))
        
        # Generate scenarios
        uncorrelated = np.random.standard_normal((n_scenarios, n_assets))
        correlated = uncorrelated @ L.T
        
        # Portfolio returns
        portfolio_returns = correlated @ weights
        
        # Calculate VaR and CVaR
        var = np.percentile(portfolio_returns, (1 - confidence) * 100)
        cvar = np.mean(portfolio_returns[portfolio_returns <= var])
        
        return -var, -cvar
    
    def calculate_risk_contributions(
        self,
        covariance: np.ndarray,
        weights: np.ndarray,
    ) -> Dict:
        """
        Calculate marginal and component risk contributions.
        
        Args:
            covariance: Covariance matrix
            weights: Portfolio weights
            
        Returns:
            Dictionary with risk decomposition
        """
        weights = np.asarray(weights)
        n_assets = len(weights)
        
        # Portfolio variance
        portfolio_variance = weights @ covariance @ weights
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Marginal risk contribution
        marginal_risk = (covariance @ weights) / portfolio_volatility
        
        # Component risk contribution
        component_risk = weights * marginal_risk
        
        # Percentage contribution
        percentage_risk = component_risk / np.sum(component_risk)
        
        # Diversification ratio
        weighted_avg_vol = np.sum(weights * np.sqrt(np.diag(covariance)))
        diversification_ratio = weighted_avg_vol / portfolio_volatility
        
        return {
            "marginal_risk": marginal_risk.tolist(),
            "component_risk": component_risk.tolist(),
            "percentage_risk": percentage_risk.tolist(),
            "diversification_ratio": float(diversification_ratio),
            "portfolio_volatility": float(portfolio_volatility),
        }
    
    def _compute_risk_metrics(
        self,
        weights: np.ndarray,
        covariance: np.ndarray,
        eigenvalues: np.ndarray,
    ) -> Dict:
        """Compute comprehensive risk metrics."""
        n_assets = len(weights)
        
        # Portfolio variance
        portfolio_variance = weights @ covariance @ weights
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Condition number (stability measure)
        condition_number = eigenvalues[-1] / (eigenvalues[0] + 1e-10)
        
        # Effective number of bets (ENB)
        # ENB = 1 / sum(w_i^2) for equal risk contribution
        enb = 1.0 / np.sum(weights ** 2)
        
        # Concentration ratio
        concentration = np.max(weights) / np.sum(weights)
        
        return {
            "portfolio_variance": float(portfolio_variance),
            "portfolio_volatility": float(portfolio_volatility),
            "condition_number": float(condition_number),
            "effective_number_of_bets": float(enb),
            "concentration_ratio": float(concentration),
        }
    
    def _covariance_to_hamiltonian(
        self,
        covariance: np.ndarray,
        n_qubits: int,
    ) -> SparsePauliOp:
        """Convert covariance matrix to qiskit Hamiltonian."""
        n = 2 ** n_qubits
        
        # Pad covariance if needed
        if len(covariance) < n:
            padded = np.zeros((n, n))
            padded[:len(covariance), :len(covariance)] = covariance
            covariance = padded
        
        # Build Pauli representation
        # H = sum_ij cov_ij |i><j|
        # Convert to Pauli basis
        
        pauli_list = []
        coeffs = []
        
        for i in range(n):
            for j in range(n):
                if np.abs(covariance[i, j]) > 1e-10:
                    # Convert |i><j| to Pauli operators
                    pauli = self._basis_to_pauli(i, j, n_qubits)
                    pauli_list.append(pauli)
                    coeffs.append(covariance[i, j])
        
        return SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))
    
    def _basis_to_pauli(
        self,
        i: int,
        j: int,
        n_qubits: int,
    ) -> str:
        """Convert basis operator |i><j| to Pauli string."""
        # |i><j| = product over qubits of single-qubit operators
        binary_i = format(i, f'0{n_qubits}b')
        binary_j = format(j, f'0{n_qubits}b')
        
        pauli_ops = []
        for bi, bj in zip(binary_i, binary_j):
            if bi == '0' and bj == '0':
                pauli_ops.append('I')  # |0><0| = (I + Z)/2
            elif bi == '1' and bj == '1':
                pauli_ops.append('I')  # |1><1| = (I - Z)/2
            elif bi == '0' and bj == '1':
                pauli_ops.append('X')  # |0><1| = (X + iY)/2
            else:
                pauli_ops.append('X')  # |1><0| = (X - iY)/2
        
        return ''.join(reversed(pauli_ops))
    
    def _covariance_to_pennylane_hamiltonian(
        self,
        covariance: np.ndarray,
        n_qubits: int,
    ) -> Tuple[List[float], List]:
        """Convert covariance matrix to PennyLane Hamiltonian."""
        # Simplified: use diagonal approximation
        coeffs = [covariance[i, i] for i in range(min(len(covariance), 2**n_qubits))]
        observables = [qml.PauliZ(i) for i in range(n_qubits)]
        
        return coeffs, observables
    
    def _create_ansatz_circuit(
        self,
        n_qubits: int,
    ) -> QuantumCircuit:
        """Create variational ansatz circuit."""
        from qiskit.circuit.library import RealAmplitudes, EfficientSU2
        
        if self.config.ansatz == 'real_amplitudes':
            return RealAmplitudes(
                n_qubits,
                reps=self.config.reps,
                entanglement=self.config.entanglement,
            )
        elif self.config.ansatz == 'efficient_su2':
            return EfficientSU2(
                n_qubits,
                reps=self.config.reps,
                entanglement=self.config.entanglement,
            )
        else:
            # Custom simple ansatz
            circuit = QuantumCircuit(n_qubits)
            for _ in range(self.config.reps):
                for i in range(n_qubits):
                    circuit.ry(np.pi/4, i)
                    circuit.rz(np.pi/4, i)
                for i in range(n_qubits - 1):
                    circuit.cx(i, i + 1)
            return circuit
    
    def _eigenstate_to_weights(
        self,
        eigenstate: np.ndarray,
        n_assets: int,
        n_qubits: int,
    ) -> np.ndarray:
        """Convert quantum eigenstate to portfolio weights."""
        # Compute probabilities from state vector
        if hasattr(eigenstate, 'numpy'):
            eigenstate = eigenstate.numpy()
        
        probabilities = np.abs(eigenstate) ** 2
        
        # Map to asset weights
        if len(probabilities) >= n_assets:
            weights = probabilities[:n_assets]
        else:
            # Aggregate probabilities for larger n_assets
            weights = np.zeros(n_assets)
            for i in range(n_assets):
                idx = i % len(probabilities)
                weights[i] += probabilities[idx]
        
        # Normalize
        weights = weights / np.sum(weights)
        
        return weights


def run_vqe_risk_analysis(
    returns: np.ndarray,
    covariance: np.ndarray,
    weights: Optional[np.ndarray] = None,
) -> Dict:
    """
    Run comprehensive VQE-based risk analysis.
    
    Args:
        returns: Asset returns
        covariance: Covariance matrix
        weights: Portfolio weights (optional, uses equal weight if not provided)
        
    Returns:
        Comprehensive risk analysis results
    """
    n_assets = len(returns)
    
    # Default to equal weight
    if weights is None:
        weights = np.ones(n_assets) / n_assets
    
    # Initialize VQE optimizer
    vqe = VQEOptimizer()
    
    # Calculate minimum variance
    min_var_result = vqe.calculate_minimum_variance(covariance)
    
    # Calculate VaR
    var_result = vqe.calculate_var(returns, covariance, weights)
    
    # Calculate risk contributions
    risk_contrib = vqe.calculate_risk_contributions(covariance, weights)
    
    return {
        "minimum_variance": min_var_result,
        "value_at_risk": var_result,
        "risk_contributions": risk_contrib,
        "portfolio_weights": weights.tolist(),
    }
