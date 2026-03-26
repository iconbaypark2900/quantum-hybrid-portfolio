"""
AWS Braket Backend for Quantum Annealing Portfolio Optimization.

This module provides:
1. Mock/simulator backend for development and testing
2. Real quantum hardware integration via AWS Braket
3. Automatic fallback to classical SA when hardware is unavailable

Configuration via environment variables:
    BRAKET_ENABLED: Enable/disable Braket integration (default: false)
    BRAKET_DEVICE_ARN: ARN of the quantum device (optional, uses simulator if not set)
    BRAKET_S3_BUCKET: S3 bucket for Braket results (required for real devices)
    BRAKET_AWS_REGION: AWS region (default: us-east-1)
    BRAKET_SHOTS: Number of shots for quantum execution (default: 100)
    BRAKET_TIMEOUT: Timeout in seconds for quantum tasks (default: 300)

Usage:
    from services.braket_backend import BraketAnnealingOptimizer

    optimizer = BraketAnnealingOptimizer()
    result = optimizer.optimize(returns, covariance)
"""

import os
import logging
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Try to import Braket SDK (optional dependency)
try:
    import boto3
    from braket.aws import AwsDevice, AwsQuantumTask
    from braket.circuits import Circuit
    from braket.tasks import QuantumTask
    from braket.device_schema import DeviceActionType
    BRAKET_AVAILABLE = True
except ImportError:
    BRAKET_AVAILABLE = False
    logger.warning("AWS Braket SDK not installed. Using classical fallback only.")


@dataclass
class BraketConfig:
    """Configuration for Braket backend."""
    enabled: bool = False
    device_arn: Optional[str] = None
    s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"
    shots: int = 100
    timeout: int = 300
    use_mock: bool = True  # Use mock/simulator by default
    mock_delay_ms: int = 500  # Simulated delay for mock execution


class BraketAnnealingOptimizer:
    """
    Quantum Annealing optimizer using AWS Braket.
    
    Falls back to classical simulated annealing when:
    - Braket SDK is not installed
    - BRAKET_ENABLED is false
    - Device is unavailable
    - Execution timeout occurs
    """

    def __init__(self, config: Optional[BraketConfig] = None):
        """
        Initialize Braket optimizer.
        
        Args:
            config: Braket configuration. If None, loads from environment.
        """
        self.config = config or self._load_config_from_env()
        self._device = None
        self._braket_client = None
        
        if self.config.enabled and BRAKET_AVAILABLE:
            self._initialize_braket()
        else:
            logger.info("Braket disabled or unavailable. Classical fallback will be used.")

    @classmethod
    def _load_config_from_env(cls) -> BraketConfig:
        """Load configuration from environment variables."""
        return BraketConfig(
            enabled=os.getenv("BRAKET_ENABLED", "false").lower() == "true",
            device_arn=os.getenv("BRAKET_DEVICE_ARN"),
            s3_bucket=os.getenv("BRAKET_S3_BUCKET"),
            aws_region=os.getenv("BRAKET_AWS_REGION", "us-east-1"),
            shots=int(os.getenv("BRAKET_SHOTS", "100")),
            timeout=int(os.getenv("BRAKET_TIMEOUT", "300")),
            use_mock=os.getenv("BRAKET_USE_MOCK", "true").lower() == "true",
            mock_delay_ms=int(os.getenv("BRAKET_MOCK_DELAY_MS", "500")),
        )

    def _initialize_braket(self):
        """Initialize Braket device and client."""
        if not BRAKET_AVAILABLE:
            logger.warning("Braket SDK not available")
            self.config.enabled = False
            return

        try:
            # Initialize AWS client
            self._braket_client = boto3.Session(
                region_name=self.config.aws_region
            ).client("braket")

            # Initialize device
            if self.config.device_arn:
                self._device = AwsDevice(self.config.device_arn)
                logger.info(f"Initialized Braket device: {self.config.device_arn}")
            else:
                # Use simulator by default
                simulator_arn = "arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6"
                try:
                    self._device = AwsDevice(simulator_arn)
                    logger.info(f"Using D-Wave simulator: {simulator_arn}")
                except Exception as e:
                    logger.warning(f"Could not initialize simulator: {e}")
                    self.config.enabled = False
                    
        except Exception as e:
            logger.warning(f"Failed to initialize Braket: {e}. Using classical fallback.")
            self.config.enabled = False

    def optimize(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        K: Optional[int] = None,
        lambda_risk: float = 1.0,
        gamma: float = 8.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Optimize portfolio using quantum annealing.
        
        Args:
            returns: Expected returns for each asset (n,)
            covariance: Covariance matrix (n, n)
            K: Number of assets to select (cardinality constraint)
            lambda_risk: Risk aversion parameter
            gamma: Penalty strength for constraints
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with optimization results
        """
        if not self.config.enabled or not self._device:
            logger.info("Using classical SA fallback")
            return self._classical_fallback(returns, covariance, K, lambda_risk, gamma)

        try:
            start_time = time.time()
            
            # Build QUBO matrix
            Q = self._build_qubo_matrix(returns, covariance, K, lambda_risk, gamma)
            
            # Convert to Ising Hamiltonian for Braket
            h, J, offset = self._qubo_to_ising(Q)
            
            # Execute on Braket device
            if self.config.use_mock or not self.config.device_arn:
                result = self._execute_mock(h, J, K)
            else:
                result = self._execute_braket(h, J, K)
            
            execution_time = time.time() - start_time
            
            # Convert binary solution to weights
            binary_solution = result['solution']
            weights = self._binary_to_weights(binary_solution, returns, covariance)
            
            # Calculate metrics
            metrics = self._calculate_metrics(weights, returns, covariance)
            
            logger.info(f"Braket optimization completed in {execution_time:.2f}s")
            
            return {
                'weights': weights,
                'sharpe_ratio': metrics['sharpe_ratio'],
                'expected_return': metrics['expected_return'],
                'volatility': metrics['volatility'],
                'n_active': metrics['n_active'],
                'backend': 'braket_quantum',
                'device': str(self._device) if self._device else 'mock',
                'execution_time': execution_time,
                'shots': result.get('shots', 0),
                'energy': result.get('energy', 0),
            }
            
        except Exception as e:
            logger.warning(f"Braket execution failed: {e}. Falling back to classical SA.")
            return self._classical_fallback(returns, covariance, K, lambda_risk, gamma)

    def _build_qubo_matrix(
        self,
        mu: np.ndarray,
        Sigma: np.ndarray,
        K: Optional[int],
        lambda_risk: float,
        gamma: float
    ) -> np.ndarray:
        """Build QUBO Q matrix for portfolio optimization."""
        n = len(mu)
        if K is None:
            K = max(1, n // 3)  # Default: select ~1/3 of assets
            
        Q = np.zeros((n, n))
        for i in range(n):
            Q[i, i] = -mu[i] + lambda_risk * Sigma[i, i] + gamma * (1 - 2 * K)
            for j in range(i + 1, n):
                Q[i, j] = Q[j, i] = lambda_risk * Sigma[i, j] + gamma
        return Q

    def _qubo_to_ising(
        self,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, Dict[Tuple[int, int], float], float]:
        """
        Convert QUBO matrix to Ising Hamiltonian format.
        
        QUBO: min x^T Q x, where x ∈ {0, 1}
        Ising: min sum(h_i * s_i) + sum(J_ij * s_i * s_j), where s ∈ {-1, 1}
        
        Returns:
            h: Linear coefficients
            J: Quadratic coefficients
            offset: Constant offset
        """
        n = Q.shape[0]
        h = np.zeros(n)
        J = {}
        offset = 0.0
        
        for i in range(n):
            h[i] += Q[i, i]
            for j in range(i + 1, n):
                J[(i, j)] = Q[i, j]
            for j in range(i):
                J[(j, i)] = Q[j, i]
        
        # Convert from {0, 1} to {-1, 1} basis
        h = h / 2
        for key in J:
            J[key] = J[key] / 4
            
        return h, J, offset

    def _execute_mock(
        self,
        h: np.ndarray,
        J: Dict[Tuple[int, int], float],
        K: int
    ) -> Dict[str, Any]:
        """
        Execute mock quantum annealing (simulated).
        
        Simulates quantum annealing behavior with classical computation.
        """
        logger.info("Executing mock quantum annealing")
        time.sleep(self.config.mock_delay_ms / 1000.0)  # Simulate latency
        
        n = len(h)
        
        # Simple simulated annealing on Ising model
        best_solution = np.random.choice([-1, 1], n)
        best_energy = self._ising_energy(best_solution, h, J)
        
        T_start = 10.0
        T_end = 0.01
        n_steps = 5000
        
        for step in range(n_steps):
            T = T_start * (T_end / T_start) ** (step / n_steps)
            
            # Flip a random spin
            idx = np.random.randint(n)
            new_solution = best_solution.copy()
            new_solution[idx] *= -1
            
            new_energy = self._ising_energy(new_solution, h, J)
            delta = new_energy - best_energy
            
            if delta < 0 or np.random.random() < np.exp(-delta / max(T, 1e-10)):
                best_solution = new_solution
                best_energy = new_energy
        
        # Convert from {-1, 1} to {0, 1}
        binary = (best_solution + 1) // 2
        
        # Ensure cardinality K
        binary = self._enforce_cardinality(binary, K)
        
        return {
            'solution': binary,
            'energy': best_energy,
            'shots': self.config.shots,
        }

    def _execute_braket(
        self,
        h: np.ndarray,
        J: Dict[Tuple[int, int], float],
        K: int
    ) -> Dict[str, Any]:
        """
        Execute on real Braket device.
        
        Requires:
        - Valid AWS credentials
        - S3 bucket for results
        - Device ARN configured
        """
        if not BRAKET_AVAILABLE:
            raise RuntimeError("Braket SDK not installed")
            
        if not self.config.s3_bucket:
            raise RuntimeError("S3 bucket not configured for Braket results")
        
        logger.info(f"Executing on Braket device: {self._device}")
        
        # Create D-Wave compatible problem
        n = len(h)
        
        # Map indices to D-Wave coordinate system (simplified)
        # In production, would need proper minor embedding
        qubit_map = {i: i for i in range(min(n, 100))}  # D-Wave limit
        
        # Submit task to Braket
        task = self._device.run(
            problem_type="ising",
            h={qubit_map[i]: float(h[i]) for i in range(n) if i in qubit_map},
            J={(qubit_map[k[0]], qubit_map[k[1]]): float(v) for k, v in J.items() 
               if k[0] in qubit_map and k[1] in qubit_map},
            shots=self.config.shots,
            s3_destination_folder=(self.config.s3_bucket, "braket-results"),
        )
        
        # Wait for result with timeout
        try:
            result = task.result(timeout=self.config.timeout)
            
            # Get best solution
            measurements = result.measurements
            if measurements is None or len(measurements) == 0:
                raise RuntimeError("No measurements returned from device")
            
            # Find lowest energy solution
            best_idx = 0
            best_energy = float('inf')
            for i, m in enumerate(measurements):
                # Convert to Ising spins
                spins = np.array([1 if bit == '1' else -1 for bit in m])
                energy = self._ising_energy(spins, h, J)
                if energy < best_energy:
                    best_energy = energy
                    best_idx = i
            
            best_solution = measurements[best_idx]
            binary = np.array([1 if b == '1' else 0 for b in best_solution])
            
            # Pad if needed
            if len(binary) < n:
                binary = np.pad(binary, (0, n - len(binary)))
            
            # Enforce cardinality
            binary = self._enforce_cardinality(binary, K)
            
            return {
                'solution': binary,
                'energy': best_energy,
                'shots': self.config.shots,
                'task_id': task.id,
            }
            
        except TimeoutError:
            task.cancel()
            raise RuntimeError(f"Braket task timed out after {self.config.timeout}s")

    def _ising_energy(
        self,
        spins: np.ndarray,
        h: np.ndarray,
        J: Dict[Tuple[int, int], float]
    ) -> float:
        """Calculate Ising Hamiltonian energy."""
        energy = np.dot(h, spins)
        for (i, j), value in J.items():
            if i < len(spins) and j < len(spins):
                energy += value * spins[i] * spins[j]
        return energy

    def _enforce_cardinality(
        self,
        binary: np.ndarray,
        K: int
    ) -> np.ndarray:
        """Ensure exactly K assets are selected."""
        n = len(binary)
        if K is None or K <= 0:
            K = max(1, n // 3)
        K = min(K, n)
        
        current_k = np.sum(binary)
        
        if current_k < K:
            # Add more assets
            zero_indices = np.where(binary == 0)[0]
            to_add = np.random.choice(zero_indices, min(K - current_k, len(zero_indices)), replace=False)
            binary[to_add] = 1
        elif current_k > K:
            # Remove excess assets
            one_indices = np.where(binary == 1)[0]
            to_remove = np.random.choice(one_indices, min(current_k - K, len(one_indices)), replace=False)
            binary[to_remove] = 0
            
        return binary

    def _binary_to_weights(
        self,
        binary: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray
    ) -> np.ndarray:
        """
        Convert binary selection to portfolio weights.
        
        Uses Markowitz optimization on selected assets.
        """
        selected = np.where(binary > 0)[0]
        n = len(returns)
        
        if len(selected) == 0:
            # Fallback to equal weight
            return np.ones(n) / n
        
        # Optimize weights on selected assets only
        from scipy.optimize import minimize
        
        mu_sel = returns[selected]
        Sigma_sel = covariance[np.ix_(selected, selected)]
        
        def neg_sharpe(w):
            r = np.dot(w, mu_sel)
            v = np.sqrt(w @ Sigma_sel @ w)
            return -r / v if v > 1e-10 else 1e10
        
        n_sel = len(selected)
        w0 = np.ones(n_sel) / n_sel
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = tuple((0, 1) for _ in range(n_sel))
        
        result = minimize(neg_sharpe, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if not result.success:
            # Fallback to equal weight on selected
            weights_sel = w0
        else:
            weights_sel = result.x
        
        # Expand to full weight vector
        weights = np.zeros(n)
        weights[selected] = weights_sel
        
        return weights

    def _classical_fallback(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        K: Optional[int],
        lambda_risk: float,
        gamma: float
    ) -> Dict[str, Any]:
        """
        Classical simulated annealing fallback.
        
        Uses the existing qubo_sa implementation.
        """
        from methods.qubo_sa import qubo_sa_weights
        
        start_time = time.time()
        
        weights = qubo_sa_weights(
            mu=returns,
            Sigma=covariance,
            K=K,
            lambda_risk=lambda_risk,
            gamma=gamma,
        )
        
        execution_time = time.time() - start_time
        metrics = self._calculate_metrics(weights, returns, covariance)
        
        return {
            'weights': weights,
            'sharpe_ratio': metrics['sharpe_ratio'],
            'expected_return': metrics['expected_return'],
            'volatility': metrics['volatility'],
            'n_active': metrics['n_active'],
            'backend': 'classical_sa',
            'execution_time': execution_time,
        }

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        returns: np.ndarray,
        covariance: np.ndarray
    ) -> Dict[str, float]:
        """Calculate portfolio performance metrics."""
        portfolio_return = float(weights @ returns)
        portfolio_variance = float(weights @ covariance @ weights)
        portfolio_volatility = np.sqrt(portfolio_variance)
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 1e-10 else 0.0
        n_active = int(np.sum(weights > 1e-4))
        
        return {
            'expected_return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'n_active': n_active,
        }

    def get_device_status(self) -> Dict[str, Any]:
        """Get current device status and configuration."""
        if not self.config.enabled:
            return {
                'status': 'disabled',
                'backend': 'classical_fallback',
                'reason': 'Braket is disabled in configuration',
            }
        
        if not BRAKET_AVAILABLE:
            return {
                'status': 'unavailable',
                'backend': 'classical_fallback',
                'reason': 'Braket SDK not installed',
            }
        
        if not self._device:
            return {
                'status': 'unavailable',
                'backend': 'classical_fallback',
                'reason': 'Device not initialized',
            }
        
        try:
            device_info = {
                'status': 'active',
                'device_name': self._device.name,
                'device_type': str(self._device.type),
                'provider': self._device.provider_name,
                'region': self.config.aws_region,
            }
            
            if self.config.use_mock:
                device_info['mode'] = 'mock/simulator'
            else:
                device_info['mode'] = 'real_hardware'
                device_info['device_arn'] = self.config.device_arn
                
            return device_info
            
        except Exception as e:
            return {
                'status': 'error',
                'backend': 'classical_fallback',
                'reason': str(e),
            }


def create_braket_optimizer(config: Optional[BraketConfig] = None) -> BraketAnnealingOptimizer:
    """Factory function to create Braket optimizer."""
    return BraketAnnealingOptimizer(config)
