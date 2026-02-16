# Getting Started

This guide walks you through installing and running the Quantum Hybrid Portfolio system.

## Prerequisites

- **Python 3.9+**
- **Node.js 16+** and npm (for the dashboard)
- **Git**

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio.git
cd quantum-hybrid-portfolio
```

### 2. Set up Python backend

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 3. Quick verification

```bash
python quick_test.py
```

Expected output: success message and basic optimization result.

### 4. Set up the dashboard (optional)

```bash
cd frontend
npm install
```

## Running the System

### Backend API only

```bash
source .venv/bin/activate
python api.py
```

The API runs at **http://localhost:5000**.

- Health check: http://localhost:5000/api/health
- OpenAPI spec: http://localhost:5000/api/docs/openapi

### Dashboard (API + Frontend)

**Terminal 1 — API:**

```bash
source .venv/bin/activate
python api.py
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm start
```

The dashboard opens at **http://localhost:3000** and proxies API requests to port 5000 (configured in `frontend/package.json`).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Set to `production` for production |
| `LOG_LEVEL` | INFO | Logging level |
| `CACHE_TTL` | 3600 | Market data cache TTL (seconds) |
| `API_KEY` | (none) | Optional API key for `X-API-Key` header |
| `REACT_APP_API_URL` | (empty) | Override API base URL (e.g. `http://localhost:5000`) |

## Next Steps

1. **Use the dashboard** — See [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)
2. **Run an example** — `python examples/basic_qsw_example.py`
3. **Call the API** — See [API_REFERENCE.md](API_REFERENCE.md)
4. **Explore notebooks** — `notebooks/01_qsw_exploration.ipynb`

## Troubleshooting

**API fails to start**

- Ensure port 5000 is free
- Check Python version: `python --version` (3.9+)
- Verify dependencies: `pip list | grep -E "flask|numpy"`

**Dashboard cannot reach API**

- Confirm API is running at http://localhost:5000
- Check `frontend/package.json` has `"proxy": "http://localhost:5000"`

**CORS errors**

- The API enables CORS for all origins in development
- For production, configure allowed origins in `api.py`

---

*Last updated: 2026-02*
