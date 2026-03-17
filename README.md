# Quantum Hybrid Portfolio

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Quantum-inspired portfolio optimization running on classical hardware.**

This project implements quantum-inspired portfolio optimization: hybrid pipelines, QUBO+SA, VQE, and classical methods, delivering robust allocations without requiring quantum hardware.

## Key Features

- **Hybrid 3-Stage Pipeline** — Screening, quantum-inspired selection, optimization (Buonaiuto/Herman 2025)
- **QUBO + Simulated Annealing** — Discrete optimization (Orús et al. 2019)
- **VQE PauliTwoDesign** — Variational quantum eigensolver-inspired weights (Scientific Reports 2023)
- **Multiple Optimization Objectives** — Equal weight, Markowitz, Min Variance, HRP, Target Return
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

All methods use the unified `run_optimization` service:

```python
from services.portfolio_optimizer import run_optimization

# Hybrid 3-stage pipeline (default)
result = run_optimization(returns, covariance, objective='hybrid')

# Classical methods
result = run_optimization(returns, covariance, objective='markowitz')   # Max Sharpe
result = run_optimization(returns, covariance, objective='min_variance')
result = run_optimization(returns, covariance, objective='hrp')          # Hierarchical Risk Parity
result = run_optimization(returns, covariance, objective='equal_weight') # 1/N baseline

# Quantum-inspired
result = run_optimization(returns, covariance, objective='qubo_sa')      # QUBO + Simulated Annealing
result = run_optimization(returns, covariance, objective='vqe')         # VQE PauliTwoDesign
result = run_optimization(returns, covariance, objective='target_return', target_return=0.10)

print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
print(f"Volatility: {result.volatility:.3f}")
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
│   ├── portfolio_optimizer.py  # Unified run_optimization (hybrid, qubo_sa, vqe, etc.)
│   ├── optimizers/             # equal_weight, markowitz, hrp, qubo_sa, vqe, hybrid_pipeline
│   ├── quantum_inspired/       # quantum_annealing (optional)
│   └── methods/                # HRP, QUBO-SA, VQE implementations
├── services/
│   ├── portfolio_optimizer.py  # Thin wrapper around core.portfolio_optimizer
│   ├── backtest.py             # Backtesting engine
│   ├── market_data.py          # Market data fetching
│   └── constraints.py          # Portfolio constraints
├── config/                     # Production settings
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
- [x] Hybrid pipeline, QUBO-SA, VQE optimizers
- [x] HRP and risk parity implementations
- [x] Interactive dashboard
- [x] Legacy objective mapping (max_sharpe→markowitz, risk_parity→hrp)

### Phase 2 (In Progress)
- [ ] Quantum linear algebra routines
- [ ] TensorFlow Quantum integration
- [ ] Performance benchmarking suite

### Phase 3 (Planned)
- [ ] Quantum machine learning models
- [ ] Market regime detection
- [ ] Full hybrid quantum-classical workflows

## Research Basis

This implementation is based on:

- **Buonaiuto/Herman (2025)** — 3-Stage Hybrid Pipeline for portfolio optimization
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
