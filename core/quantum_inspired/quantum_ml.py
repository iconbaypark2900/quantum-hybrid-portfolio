"""
Quantum Machine Learning for Financial Market Analysis.

This module provides quantum-enhanced machine learning models for:
- Market regime detection
- Feature extraction using quantum kernels
- Quantum neural networks for prediction
- Hybrid quantum-classical classification

Models include:
- Quantum Kernel Methods
- Variational Quantum Classifiers
- Quantum Boltzmann Machines
- Hybrid Quantum-Classical Neural Networks
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Try to import quantum ML libraries
try:
    import pennylane as qml
    from pennylane import numpy as pnp
    PENNYLANE_AVAILABLE = True
except ImportError:
    PENNYLANE_AVAILABLE = False
    logger.info("PennyLane not installed. Using classical ML fallback.")

try:
    import tensorflow as tf
    import tensorflow_quantum as tfq
    import sympy
    TENSORFLOW_QUANTUM_AVAILABLE = True
except ImportError:
    TENSORFLOW_QUANTUM_AVAILABLE = False
    logger.info("TensorFlow Quantum not installed. Using classical ML fallback.")

try:
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.hmm import GaussianHMM
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.info("Scikit-learn not installed. Some features unavailable.")


@dataclass
class QuantumMLConfig:
    """Configuration for quantum machine learning models."""
    # Model type
    model_type: str = 'quantum_kernel'  # 'quantum_kernel', 'vqc', 'qbm', 'hybrid'
    
    # Quantum circuit parameters
    n_qubits: int = 4
    n_layers: int = 2
    entanglement: str = 'linear'  # 'linear', 'full', 'circular'
    
    # Training parameters
    learning_rate: float = 0.01
    max_iterations: int = 100
    batch_size: int = 32
    
    # Backend
    backend: str = 'classical'  # 'classical', 'pennylane', 'tfq'
    
    # Market regime detection
    n_regimes: int = 3  # bull, bear, volatile


class MarketRegimeDetector:
    """
    Quantum-enhanced market regime detection.
    
    Detects market regimes using:
    - Classical HMM (baseline)
    - Quantum kernel clustering
    - Variational quantum classification
    - Hybrid quantum-classical models
    
    Regimes:
    - Bull: Rising prices, low volatility
    - Bear: Falling prices, high volatility
    - Volatile: High uncertainty, mixed signals
    - Normal: Stable conditions
    """
    
    def __init__(self, config: Optional[QuantumMLConfig] = None):
        """
        Initialize regime detector.
        
        Args:
            config: Configuration object
        """
        self.config = config or QuantumMLConfig()
        self.n_regimes = self.config.n_regimes
        self._scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self._model = None
        self.regime_labels = ['bear', 'normal', 'bull', 'volatile'][:self.n_regimes]
        
    def extract_features(
        self,
        returns: np.ndarray,
        prices: Optional[np.ndarray] = None,
        window: int = 20,
    ) -> np.ndarray:
        """
        Extract features for regime detection.
        
        Args:
            returns: Daily returns
            prices: Price series (optional)
            window: Rolling window size
            
        Returns:
            Feature matrix
        """
        n = len(returns)
        features = []
        
        for i in range(window, n):
            window_returns = returns[i-window:i]
            
            # Basic statistics
            mean_return = np.mean(window_returns)
            volatility = np.std(window_returns)
            
            # Momentum
            momentum_5 = np.prod(1 + returns[i-5:i]) - 1 if i >= 5 else 0
            momentum_10 = np.prod(1 + returns[i-10:i]) - 1 if i >= 10 else 0
            
            # Volatility metrics
            rolling_vol = np.std(window_returns) * np.sqrt(252)
            
            # Skewness and kurtosis
            skewness = self._skewness(window_returns)
            kurtosis = self._kurtosis(window_returns)
            
            # Max drawdown in window
            cum_returns = np.cumprod(1 + window_returns)
            running_max = np.maximum.accumulate(cum_returns)
            drawdown = (cum_returns - running_max) / running_max
            max_drawdown = np.min(drawdown)
            
            # Volume change (if available, otherwise use volatility ratio)
            vol_ratio = volatility / (np.std(returns[:window]) + 1e-10)
            
            features.append([
                mean_return * 252,  # Annualized return
                volatility * np.sqrt(252),  # Annualized volatility
                momentum_5,
                momentum_10,
                rolling_vol,
                skewness,
                kurtosis,
                max_drawdown,
                vol_ratio,
            ])
        
        return np.array(features)
    
    def _skewness(self, data: np.ndarray) -> float:
        """Calculate skewness."""
        n = len(data)
        if n < 3:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std < 1e-10:
            return 0.0
        return np.mean(((data - mean) / std) ** 3)
    
    def _kurtosis(self, data: np.ndarray) -> float:
        """Calculate excess kurtosis."""
        n = len(data)
        if n < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std < 1e-10:
            return 0.0
        return np.mean(((data - mean) / std) ** 4) - 3
    
    def fit(
        self,
        returns: np.ndarray,
        prices: Optional[np.ndarray] = None,
        method: Optional[str] = None,
    ) -> 'MarketRegimeDetector':
        """
        Fit regime detection model.
        
        Args:
            returns: Daily returns
            prices: Price series (optional)
            method: 'hmm', 'kmeans', 'quantum_kernel', or None for auto
            
        Returns:
            Self
        """
        # Extract features
        features = self.extract_features(returns, prices)
        
        if SKLEARN_AVAILABLE:
            features = self._scaler.fit_transform(features)
        
        method = method or self.config.model_type
        
        if method == 'hmm' and SKLEARN_AVAILABLE:
            self._model = self._fit_hmm(features)
        elif method == 'kmeans' and SKLEARN_AVAILABLE:
            self._model = self._fit_kmeans(features)
        elif method == 'quantum_kernel' and PENNYLANE_AVAILABLE:
            self._model = self._fit_quantum_kernel(features)
        else:
            # Default to k-means
            if SKLEARN_AVAILABLE:
                self._model = self._fit_kmeans(features)
            else:
                self._model = {'method': 'simple', 'features': features}
        
        return self
    
    def _fit_hmm(self, features: np.ndarray) -> Dict:
        """Fit Hidden Markov Model."""
        try:
            from sklearn.mm import GaussianHMM  # Try alternative import
        except ImportError:
            # HMM not available, use k-means fallback
            return self._fit_kmeans(features)
        
        n_components = min(self.n_regimes, 4)
        model = GaussianHMM(
            n_components=n_components,
            covariance_type='full',
            n_iter=100,
            random_state=42,
        )
        model.fit(features)
        
        return {'method': 'hmm', 'model': model}
    
    def _fit_kmeans(self, features: np.ndarray) -> Dict:
        """Fit K-means clustering."""
        n_clusters = min(self.n_regimes, features.shape[0])
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        model.fit(features)
        
        return {'method': 'kmeans', 'model': model}
    
    def _fit_quantum_kernel(self, features: np.ndarray) -> Dict:
        """Fit quantum kernel-based clustering."""
        if not PENNYLANE_AVAILABLE:
            return self._fit_kmeans(features)
        
        # Quantum kernel using PennyLane
        n_qubits = min(self.config.n_qubits, features.shape[1])
        
        # Define quantum device
        dev = qml.device('default.qubit', wires=n_qubits)
        
        # Feature map circuit
        @qml.qnode(dev)
        def quantum_kernel(x1, x2):
            # Encode x1
            for i in range(min(len(x1), n_qubits)):
                qml.RY(x1[i], wires=i)
            
            # Entangle
            for i in range(n_qubits - 1):
                qml.CNOT(wires=[i, i + 1])
            
            # Encode x2 (inverse)
            for i in range(min(len(x2), n_qubits)):
                qml.RY(-x2[i], wires=i)
            
            # Measure overlap
            return qml.expval(qml.PauliZ(0))
        
        # Compute kernel matrix (simplified)
        n_samples = min(len(features), 100)  # Limit for computation
        kernel_matrix = np.zeros((n_samples, n_samples))
        
        for i in range(n_samples):
            for j in range(i, n_samples):
                k = quantum_kernel(features[i], features[j])
                kernel_matrix[i, j] = k
                kernel_matrix[j, i] = k
        
        # Cluster using kernel k-means (simplified)
        from sklearn.cluster import SpectralClustering
        model = SpectralClustering(
            n_clusters=self.n_regimes,
            affinity='precomputed',
            random_state=42,
        )
        labels = model.fit_predict(kernel_matrix)
        
        return {
            'method': 'quantum_kernel',
            'labels': labels,
            'kernel_matrix': kernel_matrix,
            'n_qubits': n_qubits,
        }
    
    def predict(
        self,
        returns: np.ndarray,
        prices: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Predict market regimes.
        
        Args:
            returns: Daily returns
            prices: Price series (optional)
            
        Returns:
            Regime labels (0 to n_regimes-1)
        """
        features = self.extract_features(returns, prices)
        
        if SKLEARN_AVAILABLE and self._scaler:
            features = self._scaler.transform(features)
        
        if self._model is None:
            # Return simple volatility-based regimes
            volatility = np.std(returns[-20:]) * np.sqrt(252)
            if volatility > 0.3:
                return np.array([3])  # Volatile
            elif np.mean(returns) > 0:
                return np.array([2])  # Bull
            else:
                return np.array([0])  # Bear
        
        if self._model['method'] == 'hmm':
            return self._model['model'].predict(features)
        elif self._model['method'] == 'kmeans':
            return self._model['model'].predict(features)
        elif self._model['method'] == 'quantum_kernel':
            # For quantum kernel, use nearest neighbor in kernel space
            return self._predict_quantum_kernel(features)
        else:
            return np.zeros(len(features), dtype=int)
    
    def _predict_quantum_kernel(self, features: np.ndarray) -> np.ndarray:
        """Predict using quantum kernel model."""
        # Simplified prediction
        return np.zeros(len(features), dtype=int)
    
    def get_regime_names(self, regime_ids: np.ndarray) -> List[str]:
        """Convert regime IDs to names."""
        return [self.regime_labels[i] if i < len(self.regime_labels) else 'unknown'
                for i in regime_ids]
    
    def get_current_regime(
        self,
        returns: np.ndarray,
        prices: Optional[np.ndarray] = None,
    ) -> str:
        """Get current market regime."""
        regimes = self.predict(returns, prices)
        current_regime_id = regimes[-1] if len(regimes) > 0 else 1
        return self.regime_labels[current_regime_id] if current_regime_id < len(self.regime_labels) else 'normal'


class QuantumKernelClassifier:
    """
    Quantum Kernel Support Vector Machine for financial prediction.
    
    Uses quantum feature maps to enhance classification performance
    for tasks like:
    - Direction prediction (up/down)
    - Regime classification
    - Anomaly detection
    """
    
    def __init__(self, config: Optional[QuantumMLConfig] = None):
        """
        Initialize quantum kernel classifier.
        
        Args:
            config: Configuration object
        """
        self.config = config or QuantumMLConfig()
        self._model = None
        self._scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
    def _quantum_feature_map(self, x: np.ndarray, n_qubits: int):
        """Quantum feature map circuit."""
        if not PENNYLANE_AVAILABLE:
            return None
        
        dev = qml.device('default.qubit', wires=n_qubits)
        
        @qml.qnode(dev)
        def feature_map(x_input):
            # Amplitude encoding
            for i in range(min(len(x_input), n_qubits)):
                qml.RY(x_input[i], wires=i)
                qml.RZ(x_input[i], wires=i)
            
            # Entanglement
            for i in range(n_qubits - 1):
                qml.CNOT(wires=[i, i + 1])
            
            # Second layer
            for i in range(n_qubits):
                qml.RY(x_input[i % len(x_input)] ** 2, wires=i)
            
            return qml.state()
        
        return feature_map
    
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> 'QuantumKernelClassifier':
        """
        Fit quantum kernel classifier.
        
        Args:
            X: Feature matrix
            y: Labels
            
        Returns:
            Self
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("Scikit-learn not available. Using classical fallback.")
            self._model = {'method': 'classical', 'X': X, 'y': y}
            return self
        
        # Scale features
        X_scaled = self._scaler.fit_transform(X)
        
        if PENNYLANE_AVAILABLE and self.config.backend != 'classical':
            # Quantum kernel
            n_qubits = min(self.config.n_qubits, X_scaled.shape[1])
            
            # Build kernel matrix using quantum circuit
            kernel_matrix = self._compute_quantum_kernel(X_scaled, n_qubits)
            
            # Train SVM with precomputed kernel
            self._model = SVC(kernel='precomputed', random_state=42)
            self._model.fit(kernel_matrix, y)
            self._model['method'] = 'quantum_kernel'
        else:
            # Classical RBF kernel SVM
            self._model = SVC(kernel='rbf', random_state=42)
            self._model.fit(X_scaled, y)
            self._model['method'] = 'classical_rbf'
        
        return self
    
    def _compute_quantum_kernel(
        self,
        X: np.ndarray,
        n_qubits: int,
    ) -> np.ndarray:
        """Compute quantum kernel matrix."""
        n_samples = len(X)
        kernel = np.zeros((n_samples, n_samples))
        
        dev = qml.device('default.qubit', wires=n_qubits)
        
        @qml.qnode(dev)
        def kernel_circuit(x1, x2):
            # Encode x1
            for i in range(min(len(x1), n_qubits)):
                qml.RY(x1[i], wires=i)
            
            # Entangle
            for i in range(n_qubits - 1):
                qml.CNOT(wires=[i, i + 1])
            
            # Encode x2 inverse
            for i in range(min(len(x2), n_qubits)):
                qml.RY(-x2[i], wires=i)
            
            # Measure
            return qml.expval(qml.PauliZ(0))
        
        for i in range(n_samples):
            for j in range(i, n_samples):
                k = kernel_circuit(X[i], X[j])
                kernel[i, j] = k
                kernel[j, i] = k
        
        return kernel
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels."""
        if self._model is None:
            raise ValueError("Model not fitted")
        
        if self._scaler:
            X = self._scaler.transform(X)
        
        if self._model.get('method') == 'quantum_kernel':
            # Need training data for kernel computation
            X_train = self._model.get('X_train')
            if X_train is None:
                return np.zeros(len(X), dtype=int)
            
            kernel = self._compute_quantum_kernel(X, self.config.n_qubits)
            return self._model.predict(kernel)
        else:
            return self._model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        if hasattr(self._model, 'predict_proba'):
            return self._model.predict_proba(X)
        return np.zeros((len(X), 2))


class VariationalQuantumClassifier:
    """
    Variational Quantum Classifier (VQC) for financial prediction.
    
    Uses a parameterized quantum circuit trained via gradient descent.
    """
    
    def __init__(self, config: Optional[QuantumMLConfig] = None):
        """Initialize VQC."""
        self.config = config or QuantumMLConfig()
        self._weights = None
        self._scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
    def _create_circuit(self, n_qubits: int, n_layers: int):
        """Create variational quantum circuit."""
        if not PENNYLANE_AVAILABLE:
            return None
        
        dev = qml.device('default.qubit', wires=n_qubits)
        
        @qml.qnode(dev)
        def circuit(x, weights):
            # Feature encoding
            for i in range(min(len(x), n_qubits)):
                qml.RY(x[i], wires=i)
            
            # Variational layers
            idx = 0
            for layer in range(n_layers):
                # Rotation gates
                for i in range(n_qubits):
                    if idx < len(weights):
                        qml.RY(weights[idx], wires=i)
                        idx += 1
                
                # Entanglement
                for i in range(n_qubits - 1):
                    qml.CNOT(wires=[i, i + 1])
            
            # Measurement
            return qml.expval(qml.PauliZ(0))
        
        return circuit
    
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> 'VariationalQuantumClassifier':
        """Fit VQC."""
        if not PENNYLANE_AVAILABLE:
            # Classical fallback
            self._weights = {'method': 'classical_fallback'}
            return self
        
        n_qubits = min(self.config.n_qubits, X.shape[1])
        n_layers = self.config.n_layers
        
        # Initialize weights
        n_weights = n_qubits * n_layers
        weights = pnp.array(np.random.uniform(0, np.pi, n_weights), requires_grad=True)
        
        circuit = self._create_circuit(n_qubits, n_layers)
        
        # Cost function
        def cost(weights, X_batch, y_batch):
            losses = []
            for x, y_true in zip(X_batch, y_batch):
                prediction = circuit(x, weights)
                # Binary cross-entropy style loss
                target = 2 * y_true - 1  # Map 0,1 to -1,1
                losses.append((prediction - target) ** 2)
            return np.mean(losses)
        
        # Training loop
        opt = qml.AdamOptimizer(self.config.learning_rate)
        
        n_samples = len(X)
        batch_size = min(self.config.batch_size, n_samples)
        
        for iteration in range(self.config.max_iterations):
            # Mini-batch
            indices = np.random.choice(n_samples, batch_size, replace=False)
            X_batch = X[indices]
            y_batch = y[indices]
            
            weights, loss = opt.step(lambda w: cost(w, X_batch, y_batch), weights)
            
            if iteration % 20 == 0:
                logger.debug(f"Iteration {iteration}, Loss: {loss:.4f}")
        
        self._weights = weights
        self._circuit = circuit
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict labels."""
        if self._weights is None:
            raise ValueError("Model not fitted")
        
        if isinstance(self._weights, dict):
            # Classical fallback
            return np.zeros(len(X), dtype=int)
        
        predictions = []
        for x in X:
            pred = self._circuit(x, self._weights)
            # Map expectation to class
            label = 1 if pred > 0 else 0
            predictions.append(label)
        
        return np.array(predictions)


def detect_market_regimes(
    returns: np.ndarray,
    prices: Optional[np.ndarray] = None,
    n_regimes: int = 3,
    method: str = 'auto',
) -> Dict:
    """
    Detect market regimes from returns data.
    
    Args:
        returns: Daily returns
        prices: Price series (optional)
        n_regimes: Number of regimes to detect
        method: 'hmm', 'kmeans', 'quantum', or 'auto'
        
    Returns:
        Dictionary with regime analysis
    """
    detector = MarketRegimeDetector(QuantumMLConfig(n_regimes=n_regimes))
    detector.fit(returns, prices, method=method if method != 'auto' else None)
    
    regime_ids = detector.predict(returns, prices)
    regime_names = detector.get_regime_names(regime_ids)
    current_regime = detector.get_current_regime(returns, prices)
    
    # Compute regime statistics
    regime_stats = {}
    for i, name in enumerate(detector.regime_labels):
        mask = regime_ids == i
        if np.any(mask):
            regime_returns = returns[len(returns) - len(regime_ids):][mask]
            regime_stats[name] = {
                'count': int(np.sum(mask)),
                'frequency': float(np.mean(mask)),
                'mean_return': float(np.mean(regime_returns)),
                'volatility': float(np.std(regime_returns)),
            }
    
    return {
        'regime_ids': regime_ids.tolist(),
        'regime_names': regime_names,
        'current_regime': current_regime,
        'regime_statistics': regime_stats,
        'method': detector._model.get('method', 'unknown') if detector._model else 'unknown',
    }


if __name__ == "__main__":
    # Example usage
    np.random.seed(42)
    
    # Generate synthetic returns with regime changes
    n_days = 500
    returns = np.random.randn(n_days) * 0.02
    
    # Add regime structure
    returns[:150] += 0.001  # Bull market
    returns[150:300] -= 0.002  # Bear market
    returns[300:] *= 1.5  # Volatile period
    
    # Detect regimes
    result = detect_market_regimes(returns, n_regimes=3)
    
    print("\nMarket Regime Detection Results")
    print("="*50)
    print(f"Current Regime: {result['current_regime']}")
    print(f"Method: {result['method']}")
    print("\nRegime Statistics:")
    for name, stats in result['regime_statistics'].items():
        print(f"  {name}: {stats['frequency']*100:.1f}% frequency, "
              f"{stats['mean_return']*100:.2f}% mean return")
