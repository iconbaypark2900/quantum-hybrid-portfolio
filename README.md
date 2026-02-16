# Quantum Hybrid Portfolio

A quantum-inspired portfolio optimization system using Quantum Stochastic Walk (QSW) algorithms for risk-adjusted asset allocation. The project combines graph-based financial modeling with modern portfolio theory and exposes a REST API plus a React dashboard for optimization, backtesting, and analysis.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Overview

This system implements quantum-inspired portfolio optimization based on Quantum Stochastic Walks (QSW). It builds weighted graphs from asset returns and correlations, runs quantum-style evolution on the graph to derive allocations, and applies stability enhancement and constraints. In addition to QSW, it supports Hierarchical Risk Parity (HRP), Ledoit-Wolf covariance shrinkage, and multiple objectives (max Sharpe, min variance, target return, risk parity).

**Canonical entrypoints:** The main backend is **`api.py`** (Flask REST API). The main UI is the **React app** in `frontend/` (Quantum Portfolio Lab). Use **`serve_hf.py`** when deploying to Hugging Face Spaces.

### Key Features

- **Quantum-inspired optimization** — Quantum walk algorithms on financial graphs; configurable evolution and regime adaptation
- **Hierarchical Risk Parity (HRP)** — López de Prado method (SSRN 2708678); no matrix inversion; robust out-of-sample
- **Ledoit-Wolf shrinkage** — Robust covariance estimation for all objectives
- **Market regime adaptation** — Bull, bear, volatile, and normal regimes
- **Low turnover** — Stability enhancement to reduce trading costs
- **Live and simulated data** — yfinance integration; optional in-app simulation engine
- **REST API** — Portfolio optimize, backtest, market data, efficient frontier, ticker search, health and metrics
- **React dashboard** — Holdings, benchmarks, backtest, scenario testing, efficient frontier, correlation heatmap, in-app help

---

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+ (for the dashboard)

### Backend

```bash
git clone https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio.git
cd quantum-hybrid-portfolio

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

Quick sanity check:

```bash
python quick_test.py
```

### Dashboard (React)

```bash
cd frontend
npm install
npm start
```

The app runs at `http://localhost:3000` and expects the API at `http://localhost:5000` by default.

### Run API and dashboard together

Start the Flask API:

```bash
python api.py
```

In another terminal, build and serve the frontend, or use the development server (see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)).

---

## Basic Usage

### Python API (core)

```python
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
import numpy as np

optimizer = QuantumStochasticWalkOptimizer()
returns = np.array([0.12, 0.10, 0.15, 0.08, 0.11])
covariance = np.eye(5) * 0.04

result = optimizer.optimize(returns, covariance, market_regime='normal')
print(f"Sharpe: {result.sharpe_ratio:.3f}, Return: {result.expected_return*100:.2f}%, Vol: {result.volatility*100:.2f}%")
print("Weights:", result.weights)
```

### REST API (HTTP)

```bash
curl -X POST http://localhost:5000/api/portfolio/optimize \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL","MSFT","GOOGL"], "start_date": "2022-01-01", "end_date": "2024-12-31", "objective": "max_sharpe"}'
```

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for all endpoints.

### SDK (optional)

```python
from quantum_portfolio_sdk import QuantumPortfolioClient

client = QuantumPortfolioClient("http://localhost:5000", api_key="your-key")
health = client.health()
res = client.optimize({"tickers": ["AAPL", "MSFT", "GOOGL"], "objective": "max_sharpe", ...})
```

---

## Project Structure

```
quantum-hybrid-portfolio/
├── api.py                 # Main Flask REST API (backend for dashboard)
├── serve_hf.py            # HF Spaces entrypoint (API + static frontend)
├── config/
│   └── qsw_config.py      # QSW parameters and presets
├── core/
│   └── quantum_inspired/  # QSW optimizer, graph builder, evolution, stability, annealing
├── services/              # Backtest, market data, HRP, portfolio optimizer, constraints, data provider
├── frontend/              # React dashboard (Quantum Portfolio Lab)
│   ├── src/
│   │   ├── EnhancedQuantumDashboard.js
│   │   ├── components/dashboard/
│   │   ├── lib/simulationEngine.js
│   │   └── services/api.js
│   ├── package.json
│   └── public/
├── docs/                  # Documentation
│   ├── README.md
│   ├── GETTING_STARTED.md
│   ├── DASHBOARD_GUIDE.md
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   └── HUGGINGFACE_SPACES.md
├── examples/              # Scripts and SDK examples
├── tests/                 # Unit and integration tests
├── huggingface/           # HF Space README and metadata
├── Dockerfile.hf          # Multi-stage Dockerfile for HF Spaces
├── deploy_hf_spaces.sh    # Deploy to HF Spaces
├── requirements.txt
└── README.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Installation and first run |
| [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md) | Dashboard tabs, controls, and features |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | REST API endpoints |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md) | Deploying to Hugging Face Spaces |
| [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | Full documentation index |

---

## Deployment

### Hugging Face Spaces

To host the app on [Hugging Face Spaces](https://huggingface.co/spaces) (Docker SDK):

1. Create a new Space and choose **Docker**.
2. Use the deploy script (copies project, uses `Dockerfile.hf` and `serve_hf.py`):

```bash
./deploy_hf_spaces.sh https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE
```

See [docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md) for details.

### Local Docker

```bash
docker-compose up -d
```

Or build and run the API container manually (see `Dockerfile` and `docker-compose.yml`).

---

## Testing

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=core --cov=services --cov-report=html

# Single test file
pytest tests/test_quantum_walk.py -v
```

Frontend tests:

```bash
cd frontend && npm test
```

---

## Configuration

Key settings in `config/qsw_config.py`:

- `default_omega` — Quantum mixing (e.g. 0.3)
- `evolution_time` — Evolution steps
- `max_turnover` — Turnover cap (e.g. 0.2)
- `min_weight` / `max_weight` — Position limits

Environment variables (optional): `PORT`, `CORS_ORIGINS`, `API_KEY`, `API_KEY_REQUIRED`, `USE_LEDOIT_WOLF`, `LOG_LEVEL`. See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) and `.env.example`.

---

## How It Works (summary)

1. **Graph construction** — Nodes are assets; edges reflect correlation and diversification; weights combine correlation and return similarity.
2. **Quantum evolution** — Hamiltonian from graph Laplacian and potential; state evolution; portfolio weights from probability amplitudes.
3. **Stability** — Blending with prior weights and turnover limits to reduce trading.
4. **Constraints** — Normalization, min/max weights, long-only; optional sector and cardinality constraints via the API.

---

## References

- Chang et al. (2025) — "Quantum Stochastic Walks for Portfolio Optimization"
- López de Prado, M. (2016) — "Building Diversified Portfolios that Outperform Out-of-Sample" (SSRN 2708678), HRP
- Ledoit & Wolf (2004) — Large-dimensional covariance shrinkage
- Markowitz, H. (1952) — "Portfolio Selection"

---

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

Run tests before submitting: `pytest tests/ -v`.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

- **Organization:** Quantum Global Group
- **Repository:** https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio
- **Issues:** https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues
