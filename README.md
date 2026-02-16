# 🌌 Quantum Hybrid Portfolio

> A quantum-inspired portfolio optimization system using Quantum Stochastic Walk (QSW) algorithms for superior risk-adjusted returns.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📖 Overview

This project implements quantum-inspired portfolio optimization based on Quantum Stochastic Walks (QSW), combining principles from quantum mechanics with modern portfolio theory. The system uses graph-based representations of financial markets to find optimal asset allocations.

### Key Features

- 🎯 **Quantum-Inspired Optimization**: Uses quantum walk algorithms on financial graphs
- 🏗️ **Hierarchical Risk Parity (HRP)**: López de Prado's proven out-of-sample method (SSRN 2708678)
- 📉 **Ledoit-Wolf Shrinkage**: Robust covariance estimation for all optimizers
- 📊 **Market Regime Adaptation**: Adjusts strategy for bull/bear/volatile/normal markets  
- 🔄 **Low Turnover**: Stability enhancement reduces trading costs by up to 90%
- 📈 **Real-Time Data**: Integrates with yfinance for live S&P 500 data
- 🧪 **Validated**: Tested against Chang et al. (2025) benchmarks
- ⚡ **Fast**: Sub-second optimization for 30-asset portfolios

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio.git
cd quantum-hybrid-portfolio

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Quick Test (5 seconds)

```bash
python quick_test.py
```

### Basic Usage

```python
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
import numpy as np

# Create optimizer
optimizer = QuantumStochasticWalkOptimizer()

# Your return expectations and covariance matrix
returns = np.array([0.12, 0.10, 0.15, 0.08, 0.11])  # Expected returns
covariance = np.eye(5) * 0.04  # Covariance matrix

# Optimize portfolio
result = optimizer.optimize(returns, covariance, market_regime='normal')

# View results
print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
print(f"Expected Return: {result.expected_return*100:.2f}%")
print(f"Volatility: {result.volatility*100:.2f}%")
print(f"Weights: {result.weights}")
```

### API SDK Usage

```python
from quantum_portfolio_sdk import QuantumPortfolioClient

client = QuantumPortfolioClient("http://localhost:5000", api_key="your-key")
health = client.health()

res = client.optimize({
    "returns": [0.12, 0.10, 0.14, 0.09],
    "covariance": [
        [0.04, 0.01, 0.01, 0.00],
        [0.01, 0.05, 0.01, 0.00],
        [0.01, 0.01, 0.06, 0.01],
        [0.00, 0.00, 0.01, 0.03]
    ],
    "asset_names": ["AAPL", "MSFT", "NVDA", "JNJ"],
    "objective": "max_sharpe"
})
```

## 📊 Running Examples

### 1. Basic Portfolio Optimization
```bash
python examples/basic_qsw_example.py
```
Downloads real market data and runs QSW optimization on 30 S&P 500 stocks.

### 2. Full Validation Suite
```bash
python examples/basic_qsw_example.py
# Press Enter when prompted to run full validation
```
Validates performance against research benchmarks.

### 3. Advanced Quantum Methods
```bash
python examples/advanced_quantum_methods.py
```
Demonstrates the new quantum annealing and discrete-time quantum walk methods.

### 4. Customizable Dashboard
The React dashboard now includes extensive customization features:
- Editable dashboard titles and section headers
- Preset management for different strategies
- Theme selection (dark, ocean, forest, sunset)
- Export controls for charts and data
- Draggable metric cards
- Interactive parameter controls with real-time feedback

### 5. Unit Tests
```bash
pytest tests/test_quantum_walk.py -v
```

## 📐 Proven Portfolio Methods

In addition to the quantum-inspired approaches, the system includes two well-established methods with strong empirical and theoretical support:

### Hierarchical Risk Parity (HRP)
- López de Prado's allocation via hierarchical clustering and recursive inverse-variance bisection
- Proven lower out-of-sample variance than Markowitz CLA (SSRN 2708678)
- No matrix inversion required — works with singular or ill-conditioned covariance matrices
- Available as objective `hrp` in the API and optimizer

### Ledoit-Wolf Covariance Shrinkage
- Replaces raw sample covariance with a better-conditioned shrinkage estimator
- Automatically applied when covariance is derived from time-series data (market data fetch, backtest)
- Improves stability and out-of-sample performance for **all** objectives (max_sharpe, min_variance, risk_parity, target_return, hrp)
- Controlled via `USE_LEDOIT_WOLF` environment variable (default: enabled)

## 🧠 Advanced Quantum Methods

The upgraded version includes several advanced quantum-inspired optimization techniques:

### Quantum Annealing
- Uses quantum fluctuations to escape local minima
- Particularly effective for combinatorial portfolio problems
- Configurable parameters for temperature schedule and quantum strength

### Discrete-Time Quantum Walks
- Alternative to continuous-time evolution
- Can provide different exploration patterns of the solution space
- Useful for specific market regime conditions

### Decoherent Evolution
- Models realistic quantum systems with environmental noise
- More robust to market uncertainties
- Adjustable decoherence rates for different market conditions

## 📈 Performance Improvements

### Enhanced Evolution Dynamics
- Sparse matrix operations for large portfolios (>100 assets)
- Multiple evolution methods for different scenarios
- Improved numerical stability

### Algorithmic Enhancements
- Risk-aware Hamiltonian construction
- Additional diversification metrics
- Better constraint handling

## 📁 Project Structure

> **Canonical entrypoints:** The main backend API is `api.py`; the main UI is the React app in `frontend/`. Other files such as `enhanced_api.py`, `production_api.py`, and `dashboard.py` are legacy or experimental alternatives.

```
quantum-hybrid-portfolio/
├── config/                      # Configuration files
│   ├── __init__.py
│   └── qsw_config.py           # QSW parameters and settings
├── core/                        # Core implementation
│   └── quantum_inspired/       # Quantum-inspired algorithms
│       ├── __init__.py
│       ├── quantum_walk.py     # Main QSW optimizer
│       ├── graph_builder.py    # Financial graph construction
│       ├── evolution_dynamics.py # Quantum evolution engine
│       ├── stability_enhancer.py # Turnover reduction
│       ├── quantum_annealing.py # Quantum annealing optimizer
│       └── performance_optimizer.py # Performance optimizations
├── data/                        # Data handling
│   ├── __init__.py
│   └── sample_loader.py        # Data loading utilities
├── validation/                  # Validation framework
│   ├── __init__.py
│   └── chang_validation.py     # Chang et al. benchmarks
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── test_quantum_walk.py    # Main optimizer tests
│   ├── test_graph_builder.py   # Graph construction tests
│   ├── test_enhanced_quantum_methods.py # Enhanced quantum methods tests
│   └── phase1.py               # Integration tests
├── examples/                    # Usage examples
│   ├── basic_qsw_example.py    # Complete example
│   ├── advanced_quantum_methods.py # Advanced quantum methods
│   └── quantum_integration_example.py # Quantum computing integration
├── frontend/                    # React dashboard frontend
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── EnhancedQuantumDashboard.js # Enhanced dashboard with new features
│   │   └── App.js
│   ├── package.json
│   └── package-lock.json
├── notebooks/                   # Jupyter notebooks
│   ├── 01_qsw_exploration.ipynb
│   └── 02_chang_validation.ipynb
├── api.py                       # Backend API for dashboard
├── dashboard.py                 # Dash-based dashboard
├── quantum_portfolio_dashboard.jsx # Original React dashboard
├── requirements.txt             # Python dependencies
├── setup.py                     # Package configuration
├── quick_test.py               # Quick verification script
├── HOW_TO_RUN.md               # Detailed running instructions
├── DIRECTORY_GUIDE.md          # Complete file reference
├── TECHNICAL_DOCUMENTATION.md  # Detailed technical documentation
├── QUANTUM_INTEGRATION_ROADMAP.md # Quantum computing integration roadmap
└── README.md                    # This file
```

See [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) for detailed descriptions of each file.

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core --cov=validation --cov-report=html

# Run specific test
pytest tests/test_quantum_walk.py::TestQuantumWalk::test_optimization_basic -v

# Run integration tests
python tests/phase1.py
```

**Current Status:** 7/7 unit tests passing ✅

## 📈 Performance

### Validation Results

Based on testing with real S&P 500 data (30 stocks, 3 years):

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Sharpe Improvement | 15% avg | TBD | 🔄 In Progress |
| Turnover Reduction | 90% | 99.9% | ✅ Exceeded |
| Optimal Omega | [0.2, 0.4] | 0.10 | ⚠️ Needs Tuning |
| Regime Adaptation | Working | Working | ✅ Passed |

### Example Output

```
Expected Return: 23.73%
Volatility: 15.14%
Sharpe Ratio: 1.568
Number of assets: 30

Top 10 Holdings:
  NVDA: 3.79%
  META: 3.68%
  GOOGL: 3.65%
  ...
```

## 🎓 How It Works

### 1. Graph Construction
The system builds a weighted graph where:
- **Nodes** = Assets (stocks)
- **Edges** = Correlations between assets
- **Weights** = Combination of correlation, return similarity, and diversification benefit

### 2. Quantum Evolution
Uses quantum walk dynamics on the graph:
- **Hamiltonian**: `H = -L + ω·V` (Laplacian + potential)
- **Evolution**: `|ψ(t)⟩ = exp(-iHt)|ψ₀⟩`
- **Weights**: Extracted from probability amplitudes `|ψ(t)|²`

### 3. Stability Enhancement
Reduces portfolio turnover by blending:
- Previous portfolio weights
- New quantum-optimized weights
- Adaptive based on market volatility

### 4. Constraint Application
Ensures portfolio meets requirements:
- Weights sum to 100%
- Min/max position limits
- Long-only (no short positions)

## 🔧 Configuration

Edit `config/qsw_config.py` to customize:

```python
QSWConfig(
    default_omega=0.3,          # Quantum mixing parameter
    evolution_time=100,         # Evolution steps
    max_turnover=0.2,          # Maximum 20% turnover
    min_weight=0.001,          # 0.1% minimum position
    max_weight=0.10,           # 10% maximum position
    correlation_threshold=0.3,  # Graph edge threshold
)
```

## 📚 Documentation

- **[docs/README.md](docs/README.md)** - Documentation hub
- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and first run
- **[docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)** - Dashboard tabs, controls, and features
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - REST API endpoints
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- [HOW_TO_RUN.md](HOW_TO_RUN.md) - Running instructions
- [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) - File-by-file reference
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Full documentation index
- [notebooks/](notebooks/) - Interactive tutorials

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests before committing
pytest tests/ -v

# Check code quality
flake8 core/ validation/ tests/
black core/ validation/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Work

- Chang et al. (2025) - "Quantum Stochastic Walks for Portfolio Optimization"
- López de Prado, M. (2016) - "Building Diversified Portfolios that Outperform Out-of-Sample" (SSRN 2708678) — **HRP**
- Ledoit & Wolf (2004) - "A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices" — **Shrinkage covariance**
- Markowitz, H. (1952) - "Portfolio Selection"
- Nielsen & Chuang - "Quantum Computation and Quantum Information"

## 📧 Contact

- **Organization**: Quantum Global Group
- **Repository**: https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio
- **Issues**: https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues

## 🙏 Acknowledgments

- Chang et al. for the foundational QSW research
- NetworkX team for graph algorithms
- SciPy team for quantum evolution tools
- yfinance for market data access

## Hugging Face Spaces

Host the dashboard on [Hugging Face Spaces](https://huggingface.co/spaces):

1. Create a new Space with **Docker** SDK
2. Copy `Dockerfile.hf` to `Dockerfile` and use `huggingface/README.md` as the Space README
3. Push your code

See **[docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md)** for full instructions.

```bash
./deploy_hf_spaces.sh https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
```

## Production Deployment

### Containerized Deployment
The system includes production-ready containerization:

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run individual containers
docker build -t quantum-portfolio .
docker run -d -p 5000:5000 quantum-portfolio
```

### Production Configuration
- Security-hardened API with JWT authentication
- Rate limiting and circuit breaker patterns
- Redis caching for performance
- PostgreSQL for persistent storage
- Comprehensive logging and monitoring
- Health checks and readiness probes

### Deployment Scripts
Automated deployment scripts are included for production environments:
- `deploy_production.sh` - Complete production setup
- `Dockerfile` - Containerized application
- `docker-compose.yml` - Multi-service orchestration

---

**Status**: Production Ready 🚀  
**Version**: 1.0.0  
**Last Updated**: 2026-02-14
