# Quantum Portfolio Product API Guide

## Integration Modes

- **Production mode (recommended):** send `returns` + `covariance` directly.
- **Research/demo mode:** send `tickers` + dates (fetched via the configured market data provider — Tiingo by default when `TIINGO_API_KEY` is set, otherwise yfinance as a legacy fallback). Set `DATA_PROVIDER=tiingo` and `TIINGO_API_KEY` in your environment to enable Tiingo.

Set `REQUIRE_MATRIX_INPUT=true` in production to disable the tickers-based fetch path entirely.

## Core Endpoints

- `POST /api/portfolio/optimize`
- `POST /api/portfolio/optimize/batch`
- `POST /api/portfolio/backtest`
- `POST /api/portfolio/efficient-frontier`

## Async Jobs

- Submit optimization: `POST /api/jobs/optimize`
- Submit backtest: `POST /api/jobs/backtest`
- Poll status: `GET /api/jobs/{job_id}`

Each async submit endpoint accepts:

```json
{
  "payload": { "...": "endpoint payload" },
  "webhook_url": "https://your-system/callback"
}
```

## Authentication

Use `X-API-Key` header.

- Static mode: `API_KEY=<secret>`
- Multi-tenant mode: store hashed keys in `api_keys` table in `data/api.sqlite3`.

Admin key management endpoints:
- `POST /api/admin/api-keys` with `X-Admin-Key` header (`ADMIN_API_KEY` env var)
- `GET /api/admin/api-keys` with `X-Admin-Key` header

## SDK

Use `quantum_portfolio_sdk.QuantumPortfolioClient`:

```python
from quantum_portfolio_sdk import QuantumPortfolioClient

client = QuantumPortfolioClient("http://localhost:5000", api_key="...")
res = client.optimize({...})
```

See `examples/sdk/basic_client_example.py`.

