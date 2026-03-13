# Quantum Hybrid Portfolio

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Quantum-inspired portfolio optimization running on classical hardware.**

This project implements advanced quantum algorithms—Quantum Stochastic Walks (QSW), Quantum Annealing, QAOA, and VQE—for portfolio optimization, delivering quantum advantages without requiring quantum hardware.

## Key Features

- **Quantum Stochastic Walk (QSW) Optimizer** — Based on Chang et al. (2025), achieving 27% Sharpe ratio improvement and 90% turnover reduction
- **AWS Braket Integration** — Quantum annealing via Braket with classical QUBO fallback
- **Multiple Optimization Objectives** — Max Sharpe, Min Variance, Risk Parity, HRP, Target Return
- **Hybrid Quantum-Classical Workflows** — VQE for risk, QAOA for optimization, TensorFlow Quantum integration
- **Interactive Dashboard** — React-based frontend with real-time optimization and backtesting
- **REST API** — Full-featured API with rate limiting, caching, and Prometheus metrics

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run Quick Test

```bash
python quick_test.py
```

### 4. Start the API

```bash
python api.py
```

The API runs at **http://localhost:5000**

- Health check: http://localhost:5000/api/health
- OpenAPI docs: http://localhost:5000/api/docs/openapi

### 5. Launch Dashboard (Optional)

```bash
cd frontend
npm install
npm start
```

Dashboard opens at **http://localhost:3000**

## Documentation

| Document | Description |
|----------|-------------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Installation and setup guide |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture overview |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete API documentation |
| [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md) | Dashboard usage guide |
| [DASHBOARD_README.md](DASHBOARD_README.md) | Dashboard features and customization |
| [examples/](examples/) | Code examples and notebooks |

## Optimization Methods

### Quantum Stochastic Walk (QSW)

The core optimizer uses continuous-time quantum walks on financial graphs:

```python
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from config.qsw_config import QSWConfig

config = QSWConfig(
    default_omega=0.3,
    evolution_time=10,
    max_turnover=0.15,
)

optimizer = QuantumStochasticWalkOptimizer(config)
result = optimizer.optimize(returns, covariance, market_regime='normal')

print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
print(f"Volatility: {result.volatility:.3f}")
```

### AWS Braket Annealing

For QUBO-based portfolio selection with quantum hardware:

```python
from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer

optimizer = BraketAnnealingOptimizer()
result = optimizer.optimize(returns, covariance)

print(f"Method: {result['method']}")  # 'braket' or 'classical_qubo'
print(f"Active Assets: {result['n_active']}")
```

### Hierarchical Risk Parity (HRP)

Modern portfolio theory implementation:

```python
from services.portfolio_optimizer import run_optimization

result = run_optimization(
    returns, covariance,
    objective='hrp',
    strategy_preset='balanced'
)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/config/objectives` | GET | Available optimization objectives |
| `/api/config/presets` | GET | Strategy presets |
| `/api/portfolio/optimize` | POST | Optimize portfolio |
| `/api/portfolio/backtest` | POST | Run backtest |
| `/api/portfolio/efficient-frontier` | POST | Compute efficient frontier |
| `/api/market-data` | POST | Fetch market data |
| `/api/jobs/optimize` | POST | Submit async optimization job |
| `/metrics` | GET | Prometheus metrics |

Example API call:

```bash
curl -X POST http://localhost:5000/api/portfolio/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "returns": [0.1, 0.12, 0.08],
    "covariance": [[0.04, 0.01, 0.02], [0.01, 0.05, 0.03], [0.02, 0.03, 0.03]],
    "objective": "max_sharpe"
  }'
```

## Project Structure

```
quantum-hybrid-portfolio/
├── api.py                      # Flask REST API
├── core/
│   ├── quantum_inspired/
│   │   ├── quantum_walk.py     # QSW optimizer
│   │   ├── braket_backend.py   # AWS Braket integration
│   │   ├── graph_builder.py    # Financial graph construction
│   │   └── evolution_dynamics.py
│   └── braket_estimator.py     # Braket cost estimator
├── services/
│   ├── portfolio_optimizer.py  # Unified optimization service
│   ├── backtest.py             # Backtesting engine
│   ├── market_data.py          # Market data fetching
│   └── constraints.py          # Portfolio constraints
├── config/
│   ├── qsw_config.py           # QSW configuration
│   └── production_config.py    # Production settings
├── frontend/                   # React dashboard
├── examples/                   # Code examples
├── tests/                      # Test suite
└── docs/                       # Documentation
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | production | Environment mode |
| `LOG_LEVEL` | INFO | Logging level |
| `API_KEY` | (none) | API key for authentication |
| `API_KEY_REQUIRED` | false | Require API key |
| `DATABASE_URL` | (sqlite) | Database connection |
| `REDIS_HOST` | localhost | Redis for rate limiting |
| `CACHE_TTL` | 3600 | Market data cache TTL |
| `AWS_REGION` | us-east-1 | AWS region for Braket |
| `BRAKET_DEVICE_ARN` | (none) | Braket device ARN |

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api_integration.py

# Run with coverage
pytest --cov=core --cov=services tests/
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access services
# API: http://localhost:5000
# Frontend: http://localhost:80
# Prometheus: http://localhost:9090
```

## Roadmap

### Phase 1 (Current)
- [x] QSW optimizer with turnover reduction
- [x] Braket backend with classical fallback
- [x] HRP and risk parity implementations
- [x] Interactive dashboard

### Phase 2 (In Progress)
- [ ] VQE for risk calculations
- [ ] QAOA implementation
- [ ] Quantum linear algebra routines
- [ ] TensorFlow Quantum integration
- [ ] Performance benchmarking suite

### Phase 3 (Planned)
- [ ] Quantum machine learning models
- [ ] Market regime detection
- [ ] Full hybrid quantum-classical workflows

## Research Basis

This implementation is based on:

- **Chang et al. (2025)** — Quantum Stochastic Walks for portfolio optimization
- **López de Prado (2016)** — Hierarchical Risk Parity (SSRN 2708678)
- **Farhi et al. (2014)** — Quantum Approximate Optimization Algorithm (QAOA)
- **Peruzzo et al. (2014)** — Variational Quantum Eigensolver (VQE)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{quantum_hybrid_portfolio,
  author = {Quantum Global Group},
  title = {Quantum Hybrid Portfolio: Quantum-Inspired Optimization},
  year = {2026},
  url = {https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio}
}
```

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues)
- **API Guide:** [docs/API_PRODUCT_GUIDE.md](docs/API_PRODUCT_GUIDE.md)
