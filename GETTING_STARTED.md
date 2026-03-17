# 🌌 Quantum Hybrid Portfolio - Getting Started

Welcome to the Quantum Hybrid Portfolio optimization system! This project implements quantum-inspired portfolio optimization: hybrid pipelines, QUBO+SA, VQE, and classical methods.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio.git
cd quantum-hybrid-portfolio

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Quick Verification

```bash
# Test that the system works
python quick_test.py
```

### Run Example

```bash
# Run full example with real market data
python examples/basic_qsw_example.py
# Or integration example comparing all methods
python examples/quantum_integration_example.py  # or examples/quantum_integration_example.py
```

## 🔬 How It Works

This system uses a unified `run_optimization` service that routes to:

1. **Hybrid Pipeline**: 3-stage screening, quantum-inspired selection, optimization
2. **QUBO+SA**: Discrete portfolio selection via QUBO and simulated annealing
3. **VQE**: Variational quantum eigensolver-inspired weights
4. **Classical**: Markowitz, Min Variance, HRP, Equal Weight

## 📊 Key Components

### Core Modules:
- `core.portfolio_optimizer`: Unified `run_optimization` entry point
- `core.optimizers`: equal_weight, markowitz, hrp, qubo_sa, vqe, hybrid_pipeline
- `services.portfolio_optimizer`: Thin wrapper for backward compatibility

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_optimizers.py tests/test_api_integration.py -v
```

## 📈 Usage Example

```python
from services.portfolio_optimizer import run_optimization
import numpy as np

# Prepare data
returns = np.array([0.12, 0.10, 0.15, 0.08, 0.11])
covariance = np.eye(5) * 0.04

# Optimize (hybrid is default)
result = run_optimization(returns, covariance, objective='hybrid')

# Other objectives: markowitz, min_variance, hrp, qubo_sa, vqe, equal_weight
print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
print(f"Expected Return: {result.expected_return*100:.2f}%")
print(f"Volatility: {result.volatility*100:.2f}%")
```

## 🎯 Key Features

- **Hybrid Pipeline**: 3-stage quantum-inspired optimization
- **Multiple Objectives**: Hybrid, QUBO-SA, VQE, Markowitz, HRP, Equal Weight
- **Real-World Ready**: Uses live S&P 500 data from yfinance
- **Validated**: Benchmarked against López de Prado HRP and classical methods

## 📁 Project Structure

- `core/`: Unified optimizers and portfolio_optimizer
- `methods/`: HRP, QUBO-SA, VQE implementations
- `examples/`: Usage examples with real data
- `tests/`: Comprehensive test suite

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

---

**Status**: Production Ready | **Tests**: 7/7 Passing | **Performance**: Validated