"""
AWS Braket backend for quantum annealing-based portfolio optimization.

Provides:
- BraketAnnealingOptimizer: Main optimizer class with Braket and classical fallback
- build_qubo_portfolio: Build QUBO formulation for binary asset selection
- run_braket_portfolio_optimization: Submit to Braket or solve classically

When AWS Braket is unavailable, falls back to classical QUBO solver.
"""
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Try to import AWS Braket SDK
try:
    import boto3
    from braket.aws import AwsDevice
    from braket.circuits import Circuit
    from braket.tasks import QuantumTask
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False
    logger.warning(
        "AWS Braket SDK not installed. Install with: pip install amazon-braket-sdk"
    )


@dataclass
class QUBOPortfolioConfig:
    """Configuration for QUBO portfolio optimization."""
    # QUBO formulation parameters
    risk_aversion: float = 0.5  # Trade-off between risk and return (0-1)
    penalty_budget: float = 100.0  # Penalty for budget constraint violation
    penalty_cardinality: float = 50.0  # Penalty for cardinality constraint
    
    # Braket-specific parameters
    shots_per_task: int = 1000
    device_name: str = "rigetti_ankaa"  # Default QPU device
    
    # Classical fallback parameters
    max_iterations: int = 1000
    num_random_restarts: int = 10
    
    # Portfolio constraints
    max_assets: int = 64  # Maximum assets for QUBO (QPU qubit limit)
    min_assets: Optional[int] = None  # Minimum number of assets
    max_assets_target: Optional[int] = None  # Target maximum number of assets


class BraketAnnealingOptimizer:
    """
    AWS Braket quantum annealing optimizer for portfolio selection.
    
    Formulates portfolio optimization as a QUBO (Quadratic Unconstrained 
    Binary Optimization) problem and solves it using:
    1. AWS Braket quantum hardware (when available)
    2. Classical QUBO solver (fallback)
    
    The QUBO formulation encodes binary asset selection (include/exclude)
    with objectives for maximizing return and minimizing risk.
    """
    
    def __init__(self, config: Optional[QUBOPortfolioConfig] = None):
        """
        Initialize Braket optimizer.
        
        Args:
            config: Configuration object. Uses defaults if not provided.
        """
        self.config = config or QUBOPortfolioConfig()
        self._device = None
        
    def optimize(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        market_regime: str = 'normal',
        initial_weights: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Optimize portfolio using Braket annealing or classical fallback.
        
        Args:
            returns: Expected returns for each asset
            covariance: Covariance matrix
            market_regime: Market regime (not used in QUBO, kept for interface)
            initial_weights: Starting weights (for turnover tracking)
            
        Returns:
            Dictionary with optimization results including:
            - weights: Optimized portfolio weights
            - sharpe_ratio: Portfolio Sharpe ratio
            - expected_return: Portfolio expected return
            - volatility: Portfolio volatility
            - n_active: Number of active positions
            - method: "braket" or "classical_qubo"
        """
        returns = np.asarray(returns)
        covariance = np.asarray(covariance)
        n_assets = len(returns)
        
        # Limit to max_assets for QUBO formulation
        if n_assets > self.config.max_assets:
            logger.warning(
                f"Reducing assets from {n_assets} to {self.config.max_assets} "
                "(QUBO qubit limit). Selecting top assets by expected return."
            )
            top_indices = np.argsort(returns)[-self.config.max_assets:]
            returns = returns[top_indices]
            covariance = covariance[np.ix_(top_indices, top_indices)]
            n_assets = self.config.max_assets
        
        # Build QUBO formulation
        linear, quadratic = build_qubo_portfolio(
            returns, covariance, self.config
        )
        
        # Run optimization
        result = run_braket_portfolio_optimization(
            linear, quadratic, n_assets, self.config
        )
        
        # Convert binary selection to weights
        binary_selection = result["binary_selection"]
        weights = self._binary_to_weights(
            binary_selection, returns, covariance
        )
        
        # Calculate portfolio metrics
        metrics = self._calculate_metrics(weights, returns, covariance)
        
        # Map back to original asset space if we reduced
        if len(weights) < n_assets:
            full_weights = np.zeros(n_assets)
            full_weights[:len(weights)] = weights
            weights = full_weights
        
        return {
            "weights": weights,
            "sharpe_ratio": metrics["sharpe_ratio"],
            "expected_return": metrics["expected_return"],
            "volatility": metrics["volatility"],
            "n_active": metrics["n_active"],
            "method": result["method"],
            "turnover": result.get("turnover", 0.0),
        }
    
    def _binary_to_weights(
        self,
        binary_selection: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray,
    ) -> np.ndarray:
        """
        Convert binary asset selection to portfolio weights.
        
        Uses inverse variance weighting for selected assets.
        
        Args:
            binary_selection: Binary array indicating selected assets
            returns: Expected returns
            covariance: Covariance matrix
            
        Returns:
            Normalized portfolio weights
        """
        selected_indices = np.where(binary_selection > 0)[0]
        n_selected = len(selected_indices)
        
        if n_selected == 0:
            # Fallback to equal weight
            return np.ones(len(binary_selection)) / len(binary_selection)
        
        if n_selected == 1:
            # Single asset gets 100%
            weights = np.zeros(len(binary_selection))
            weights[selected_indices[0]] = 1.0
            return weights
        
        # Extract sub-matrix for selected assets
        selected_cov = covariance[np.ix_(selected_indices, selected_indices)]
        
        # Inverse variance weighting
        variances = np.diag(selected_cov)
        inv_variances = 1.0 / (variances + 1e-10)
        weights_selected = inv_variances / np.sum(inv_variances)
        
        # Construct full weight vector
        weights = np.zeros(len(binary_selection))
        weights[selected_indices] = weights_selected
        
        return weights
    
    def _calculate_metrics(
        self,
        weights: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray,
    ) -> Dict:
        """Calculate portfolio performance metrics."""
        portfolio_return = float(np.dot(weights, returns))
        portfolio_variance = float(weights @ covariance @ weights)
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        if portfolio_volatility > 1e-10:
            sharpe_ratio = portfolio_return / portfolio_volatility
        else:
            sharpe_ratio = 0.0
        
        n_active = int(np.sum(weights > 0.01))  # Count assets with >1% weight
        
        return {
            "expected_return": portfolio_return,
            "volatility": portfolio_volatility,
            "sharpe_ratio": sharpe_ratio,
            "n_active": n_active,
        }


def build_qubo_portfolio(
    returns: np.ndarray,
    covariance: np.ndarray,
    config: QUBOPortfolioConfig,
) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float]]:
    """
    Build QUBO formulation for binary asset selection.
    
    The QUBO objective is:
        minimize: -lambda * return + (1-lambda) * risk + penalty * constraints
    
    Where:
    - lambda is the risk aversion parameter
    - return = sum_i (r_i * x_i) where x_i is binary (0/1)
    - risk = sum_ij (sigma_ij * x_i * x_j)
    - constraints enforce budget and cardinality
    
    Args:
        returns: Expected returns for each asset
        covariance: Covariance matrix
        config: QUBO configuration
        
    Returns:
        Tuple of (linear_terms, quadratic_terms) where:
        - linear_terms: Dict mapping index -> coefficient
        - quadratic_terms: Dict mapping (i,j) -> coefficient
    """
    n = len(returns)
    
    # Normalize inputs for numerical stability
    returns_norm = returns / (np.max(np.abs(returns)) + 1e-10)
    cov_norm = covariance / (np.max(np.abs(covariance)) + 1e-10)
    
    linear = {}
    quadratic = {}
    
    # Objective: maximize return, minimize risk
    # QUBO minimizes, so we negate the return term
    lambda_ = config.risk_aversion
    
    # Linear terms from returns (negative because we maximize return)
    for i in range(n):
        linear[i] = -lambda_ * returns_norm[i]
    
    # Quadratic terms from covariance (risk)
    for i in range(n):
        for j in range(i, n):
            if i == j:
                # Diagonal: add to linear term (x_i^2 = x_i for binary)
                linear[i] = linear.get(i, 0) + (1 - lambda_) * cov_norm[i, i]
            else:
                # Off-diagonal quadratic terms
                quadratic[(i, j)] = (1 - lambda_) * cov_norm[i, j]
    
    # Budget constraint: sum(x_i) = 1
    # Penalty: P * (sum(x_i) - 1)^2
    # = P * (sum(x_i^2) + 2*sum(x_i*x_j) - 2*sum(x_i) + 1)
    # For binary x_i: x_i^2 = x_i
    # = P * (sum(x_i) + 2*sum(x_i*x_j) - 2*sum(x_i) + 1)
    # = P * (-sum(x_i) + 2*sum(x_i*x_j) + 1)
    P_budget = config.penalty_budget
    
    for i in range(n):
        linear[i] = linear.get(i, 0) - P_budget
    
    for i in range(n):
        for j in range(i + 1, n):
            key = (i, j)
            quadratic[key] = quadratic.get(key, 0) + 2 * P_budget
    
    # Cardinality constraint (optional): target number of assets
    if config.max_assets_target is not None:
        k = config.max_assets_target
        P_card = config.penalty_cardinality
        
        # Penalty: P * (sum(x_i) - k)^2
        for i in range(n):
            linear[i] = linear.get(i, 0) + P_card * (1 - 2 * k)
        
        for i in range(n):
            for j in range(i + 1, n):
                key = (i, j)
                quadratic[key] = quadratic.get(key, 0) + 2 * P_card
    
    return linear, quadratic


def run_braket_portfolio_optimization(
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
    n_variables: int,
    config: QUBOPortfolioConfig,
) -> Dict:
    """
    Run portfolio optimization via Braket or classical fallback.
    
    Args:
        linear: Linear QUBO coefficients
        quadratic: Quadratic QUBO coefficients
        n_variables: Number of binary variables
        config: Configuration
        
    Returns:
        Dictionary with:
        - binary_selection: Binary array of selected assets
        - method: "braket" or "classical_qubo"
        - energy: Final QUBO energy (objective value)
    """
    # Try Braket first if available
    if BRAKET_AVAILABLE:
        try:
            result = _run_on_braket(linear, quadratic, n_variables, config)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Braket optimization failed: {e}. Using classical fallback.")
    
    # Classical fallback
    return _solve_qubo_classically(linear, quadratic, n_variables, config)


def _run_on_braket(
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
    n_variables: int,
    config: QUBOPortfolioConfig,
) -> Optional[Dict]:
    """
    Submit QUBO to AWS Braket for quantum annealing.
    
    Note: This is a placeholder for actual Braket integration.
    Current Braket devices are gate-based, not annealing-based.
    For production, you would use Braket's annealing solver or
    convert to gate-based QAOA.
    
    Returns None if Braket is not configured or fails.
    """
    if not BRAKET_AVAILABLE:
        return None
    
    # Check for Braket credentials
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    device_arn = os.environ.get("BRAKET_DEVICE_ARN")
    
    if not device_arn:
        logger.info("No Braket device ARN configured. Using classical fallback.")
        return None
    
    try:
        # Initialize Braket device
        device = AwsDevice(device_arn)
        
        # Convert QUBO to Ising model for annealing
        # QUBO: sum_i a_i x_i + sum_ij b_ij x_i x_j
        # Ising: sum_i h_i s_i + sum_ij J_ij s_i s_j
        # where x_i = (1 + s_i) / 2, s_i in {-1, +1}
        
        h, J = _qubo_to_ising(linear, quadratic, n_variables)
        
        # Submit to Braket annealing device
        # Note: Actual implementation depends on device type
        # This is a simplified example
        
        logger.info(f"Submitting QUBO to Braket device: {device_arn}")
        
        # For gate-based devices, would use QAOA circuit instead
        # This is placeholder code showing the interface
        
        task = device.run(
            circuit=_build_qaoa_circuit(h, J, n_variables),
            shots=config.shots_per_task,
        )
        
        result = task.result()
        
        # Parse results
        measurements = result.measurements
        binary_selection = _parse_braket_measurements(measurements, n_variables)
        
        # Calculate energy
        energy = _compute_qubo_energy(binary_selection, linear, quadratic)
        
        return {
            "binary_selection": binary_selection,
            "method": "braket",
            "energy": energy,
        }
        
    except Exception as e:
        logger.error(f"Braket execution failed: {e}")
        return None


def _build_qaoa_circuit(
    h: Dict[int, float],
    J: Dict[Tuple[int, int], float],
    n_qubits: int,
    p: int = 1,
) -> 'Circuit':
    """
    Build QAOA circuit for gate-based quantum device.
    
    Args:
        h: Ising linear coefficients (local fields)
        J: Ising quadratic coefficients (couplings)
        n_qubits: Number of qubits
        p: QAOA depth (number of layers)
        
    Returns:
        Braket Circuit object
    """
    if not BRAKET_AVAILABLE:
        raise ImportError("Braket SDK required for circuit construction")
    
    circuit = Circuit()
    
    # Initialize in superposition
    for i in range(n_qubits):
        circuit.h(i)
    
    # QAOA layers
    for layer in range(p):
        # Problem Hamiltonian (phase separation)
        for i in range(n_qubits):
            if i in h:
                circuit.rz(i, h[i])
        
        for (i, j), coupling in J.items():
            if i < n_qubits and j < n_qubits:
                circuit.cnot(i, j)
                circuit.rz(j, coupling)
                circuit.cnot(i, j)
        
        # Mixer Hamiltonian
        for i in range(n_qubits):
            circuit.rx(i, np.pi / 2)
    
    # Measure all qubits
    circuit.measure_all()
    
    return circuit


def _qubo_to_ising(
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
    n_variables: int,
) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float]]:
    """
    Convert QUBO formulation to Ising model.
    
    QUBO: x_i in {0, 1}
    Ising: s_i in {-1, +1}
    Transformation: x_i = (1 + s_i) / 2
    
    Args:
        linear: QUBO linear coefficients
        quadratic: QUBO quadratic coefficients
        n_variables: Number of variables
        
    Returns:
        Tuple of (h, J) for Ising model
    """
    h = {}
    J = {}
    
    # Convert linear terms
    for i in range(n_variables):
        a_i = linear.get(i, 0)
        h[i] = a_i / 2
        
    # Convert quadratic terms and adjust linear
    for (i, j), b_ij in quadratic.items():
        J[(i, j)] = b_ij / 4
        h[i] = h.get(i, 0) + b_ij / 4
        h[j] = h.get(j, 0) + b_ij / 4
    
    # Add constant offset (not needed for optimization)
    # constant = sum_i (a_i / 2) + sum_ij (b_ij / 4)
    
    return h, J


def _parse_braket_measurements(
    measurements: np.ndarray,
    n_variables: int,
) -> np.ndarray:
    """
    Parse Braket measurement results to get best binary solution.
    
    Args:
        measurements: Array of shape (shots, n_variables)
        n_variables: Number of variables
        
    Returns:
        Best binary selection found
    """
    # Count occurrences of each bitstring
    from collections import Counter
    
    bitstrings = [tuple(m) for m in measurements]
    counts = Counter(bitstrings)
    
    # Return most frequent bitstring
    best_bitstring = counts.most_common(1)[0][0]
    
    return np.array(best_bitstring)


def _solve_qubo_classically(
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
    n_variables: int,
    config: QUBOPortfolioConfig,
) -> Dict:
    """
    Solve QUBO using classical optimization.
    
    Uses simulated annealing with multiple random restarts.
    
    Args:
        linear: Linear QUBO coefficients
        quadratic: Quadratic QUBO coefficients
        n_variables: Number of binary variables
        config: Configuration
        
    Returns:
        Dictionary with binary_selection, method="classical_qubo", and energy
    """
    best_solution = None
    best_energy = float('inf')
    
    for restart in range(config.num_random_restarts):
        solution, energy = _simulated_annealing_qubo(
            linear, quadratic, n_variables, config
        )
        
        if energy < best_energy:
            best_energy = energy
            best_solution = solution
    
    return {
        "binary_selection": best_solution,
        "method": "classical_qubo",
        "energy": best_energy,
    }


def _simulated_annealing_qubo(
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
    n_variables: int,
    config: QUBOPortfolioConfig,
) -> Tuple[np.ndarray, float]:
    """
    Solve QUBO using simulated annealing.
    
    Args:
        linear: Linear QUBO coefficients
        quadratic: Quadratic QUBO coefficients
        n_variables: Number of variables
        config: Configuration
        
    Returns:
        Tuple of (best_solution, best_energy)
    """
    # Initialize random solution
    current = np.random.randint(0, 2, n_variables)
    current_energy = _compute_qubo_energy(current, linear, quadratic)
    
    best = current.copy()
    best_energy = current_energy
    
    # Annealing schedule
    T_initial = 100.0
    T_final = 0.1
    cooling_rate = 0.95
    
    T = T_initial
    iteration = 0
    
    while T > T_final and iteration < config.max_iterations:
        # Generate neighbor by flipping one bit
        neighbor = current.copy()
        flip_idx = np.random.randint(0, n_variables)
        neighbor[flip_idx] = 1 - neighbor[flip_idx]
        
        neighbor_energy = _compute_qubo_energy(neighbor, linear, quadratic)
        
        # Accept or reject
        delta = neighbor_energy - current_energy
        
        if delta < 0 or np.random.random() < np.exp(-delta / T):
            current = neighbor
            current_energy = neighbor_energy
            
            if current_energy < best_energy:
                best = current.copy()
                best_energy = current_energy
        
        T *= cooling_rate
        iteration += 1
    
    return best, best_energy


def _compute_qubo_energy(
    solution: np.ndarray,
    linear: Dict[int, float],
    quadratic: Dict[Tuple[int, int], float],
) -> float:
    """
    Compute QUBO energy for a given binary solution.
    
    Energy = sum_i (a_i * x_i) + sum_ij (b_ij * x_i * x_j)
    
    Args:
        solution: Binary array
        linear: Linear coefficients
        quadratic: Quadratic coefficients
        
    Returns:
        Energy value
    """
    energy = 0.0
    
    # Linear terms
    for i, coef in linear.items():
        if i < len(solution):
            energy += coef * solution[i]
    
    # Quadratic terms
    for (i, j), coef in quadratic.items():
        if i < len(solution) and j < len(solution):
            energy += coef * solution[i] * solution[j]
    
    return float(energy)


# Import os at module level for Braket functions
import os
