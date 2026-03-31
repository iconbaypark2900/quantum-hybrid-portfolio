# API Reference

The Quantum Hybrid Portfolio API is a Flask REST API running on port 5000 by default.

## Base URL

- **Local:** `http://localhost:5000`
- **Health:** `GET /api/health`

## Authentication

Optional API key via header:

```
X-API-Key: <your-api-key>
```

Set `API_KEY` environment variable on the server for static key validation.

When `API_KEY_REQUIRED=true`, clients must send `X-API-Key` on protected routes. `GET /api/health` and `GET /metrics` remain usable for probes without a key (see route decorators in `api/app.py`).

---

## Response envelope

Most JSON routes wrap payloads in a **standard envelope** (`success_response` / `error_response` in `api/app.py`):

**Success (2xx)**

```json
{
  "data": {},
  "meta": {
    "request_id": "<uuid>",
    "duration_ms": 12.34
  }
}
```

The **Next.js** client (`web/src/lib/api.ts`) and **CRA** client (`frontend/src/services/api.js`) unwrap `data` in a response interceptor, so application code typically sees the inner payload only.

**Error (4xx / 5xx)**

```json
{
  "error": { "code": "ERROR_CODE", "message": "Human-readable message" },
  "meta": { "request_id": "<uuid>" }
}
```

**Exceptions:** `GET /metrics` returns Prometheus text (no JSON envelope). Machine-readable contract: `GET /api/docs/openapi`.

---

## Web client contract (migration Phase 1)

**Must-not-break** for the Next.js app (`web/`) and CRA dashboard (`frontend/`): changing method, path, auth requirement, or the **shape of the unwrapped `data` payload** for these routes requires coordination (version bump, dual support, or client updates). Automated checks: `scripts/test_api_integration.py`, `tests/test_api_integration.py`.

| Endpoint | Method | Auth | Notes |
|----------|--------|------|--------|
| `/api/health` | GET | No key required | Rate limit exempt. |
| `/api/config/objectives` | GET | If `API_KEY_REQUIRED` | Optimization objective list. |
| `/api/config/presets` | GET | If required | Preset configurations. |
| `/api/config/constraints` | GET | If required | Constraint schema. |
| `/api/config/ibm-quantum` | POST | If required | Body: `{ "token": "..." }`. |
| `/api/config/ibm-quantum` | DELETE | If required | Clears stored token. |
| `/api/config/ibm-quantum/status` | GET | If required | Connection status. |
| `/api/config/ibm-quantum/workloads` | GET | Yes | Query `limit` (default 20, max 100). Lists IBM Runtime jobs for the tenant token. |
| `/api/market-data` | POST | If required | Historical returns / covariance inputs. |
| `/api/portfolio/optimize` | POST | If required | Single optimization run. |
| `/api/portfolio/optimize/batch` | POST | If required | Batch optimize. |
| `/api/portfolio/backtest` | POST | If required | Backtest. |
| `/api/portfolio/backtest/batch` | POST | If required | Batch backtest. |
| `/api/portfolio/efficient-frontier` | POST | If required | Efficient frontier points. |
| `/api/runs` | POST | If required | Create a durable lab run (async optimization). Returns `run_id`. |
| `/api/runs` | GET | If required | List recent lab runs for the tenant. Query `limit` (default 20). |
| `/api/runs/<id>` | GET | If required | Fetch run status, spec, and result (tenant-scoped). |

---

## Environment variables (Flask server vs Next.js)

| Variable | Where | Purpose |
|----------|--------|---------|
| `PORT` | Flask (server) | API listen port (default 5000). |
| `API_KEY`, `API_KEY_REQUIRED` | Flask (server) | Static API key validation. |
| `DATABASE_URL`, `REDIS_*`, etc. | Flask (server) | Backend only; never expose to the browser bundle. |
| `NEXT_PUBLIC_API_URL` | Next.js (build-time / browser) | Base URL for the Flask API (e.g. `http://127.0.0.1:5000`). Empty string = same origin (use when a dev proxy forwards `/api` to Flask). |
| `NEXT_PUBLIC_API_KEY` | Next.js (browser) | Optional; sent as `X-API-Key` if set. Treat as sensitive if the app is public; prefer same-origin proxy and server-side secrets for production. |

Copy `.env.example` to `.env` for Flask. For the Next app, use `web/.env.local` (see Next.js docs); only `NEXT_PUBLIC_*` variables are embedded in client bundles.

---

## Endpoints

### Health

#### `GET /api/health`

Returns API health and dependency checks. Uses the **standard envelope**; below is the shape of **`data`** after unwrapping (see [Response envelope](#response-envelope)).

**`data` payload (illustrative):**

```json
{
  "status": "healthy",
  "checks": { "api": "ok", "market_data": "available" },
  "details": { "version": "1.0.0", "timestamp": "2026-02-15T12:00:00Z" },
  "cache_entries": 0,
  "message": "Quantum Portfolio Backend is running"
}
```

---

### Market Data

#### `POST /api/market-data`

Fetch historical market data for given tickers.

**Request:**

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31"
}
```

**Response:** Returns returns matrix, covariance, asset names, dates.

---

### Portfolio Optimization

#### `POST /api/portfolio/optimize`

Run QSW portfolio optimization.

**Request:**

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "objective": "max_sharpe",
  "omega": 0.3,
  "evolution_time": 10,
  "max_weight": 0.1,
  "turnover_limit": 0.2,
  "regime": "normal",
  "strategy_preset": "balanced",
  "constraints": {
    "max_weight": 0.1,
    "turnover_limit": 0.2,
    "min_weight": 0.001
  },
  "target_return": 0.08
}
```

**Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `tickers` | string[] | Asset symbols |
| `start_date` | string | YYYY-MM-DD |
| `end_date` | string | YYYY-MM-DD |
| `objective` | string | `max_sharpe`, `min_variance`, `risk_parity`, `hrp`, `target_return` |
| `omega` | number | Quantum mixing (0.05–0.6) |
| `evolution_time` | number | Evolution steps |
| `max_weight` | number | Max position (e.g. 0.1 = 10%) |
| `turnover_limit` | number | Max turnover per rebalance |
| `regime` | string | `normal`, `bull`, `bear`, `volatile` |
| `strategy_preset` | string | `balanced`, `conservative`, etc. |
| `target_return` | number | Required when `objective=target_return` |

**Response:**

```json
{
  "qsw_result": {
    "weights": [0.05, 0.12, ...],
    "sharpe_ratio": 1.45,
    "expected_return": 0.12,
    "volatility": 0.15,
    "n_active": 18
  },
  "holdings": [
    { "name": "AAPL", "weight": 0.05, "sector": "Technology" }
  ],
  "benchmarks": { ... },
  "assets": [ ... ]
}
```

---

### Batch Optimization

#### `POST /api/portfolio/optimize/batch`

Run multiple optimizations in one request.

**Request:**

```json
{
  "requests": [
    { "tickers": ["AAPL", "MSFT"], "start_date": "2020-01-01", "end_date": "2024-12-31", "omega": 0.2 },
    { "tickers": ["AAPL", "MSFT"], "start_date": "2020-01-01", "end_date": "2024-12-31", "omega": 0.4 }
  ],
  "stop_on_error": false
}
```

**Response:**

```json
{
  "results": [
    { "status": "ok", "result": { ... } },
    { "status": "ok", "result": { ... } }
  ]
}
```

---

### Backtest

#### `POST /api/portfolio/backtest`

Run historical backtest.

**Request:**

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "objective": "max_sharpe",
  "strategy_preset": "balanced",
  "rebalance_frequency": "monthly",
  "constraints": { "max_weight": 0.1 }
}
```

**Response:**

```json
{
  "total_return": 0.45,
  "annual_return": 0.12,
  "sharpe_ratio": 1.2,
  "max_drawdown": 0.15,
  "volatility": 0.18,
  "equity_curve": [
    { "date": "2020-01-02", "portfolio_value": 100000 },
    ...
  ]
}
```

---

### Batch Backtest

#### `POST /api/portfolio/backtest/batch`

Run multiple backtests (e.g. for Scenario Tester).

**Request:**

```json
{
  "requests": [
    { "tickers": ["SPY"], "start_date": "2020-01-01", "end_date": "2024-12-31" },
    { "tickers": ["QQQ"], "start_date": "2020-01-01", "end_date": "2024-12-31" }
  ],
  "stop_on_error": false
}
```

---

### Efficient Frontier

#### `POST /api/portfolio/efficient-frontier`

Compute efficient frontier points.

**Request:**

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "n_points": 20
}
```

**Response:**

```json
{
  "frontier_points": [
    { "volatility": 0.12, "target_return": 0.08 },
    ...
  ]
}
```

---

### Configuration

#### `GET /api/config/objectives`

Returns available optimization objectives.

#### `GET /api/config/constraints`

Returns constraint schema (max_weight, turnover_limit, etc.).

#### `GET /api/config/presets`

Returns strategy presets (balanced, conservative, etc.).

---

### Ticker Search

#### `GET /api/tickers/search?q=AAP`

Search ticker catalog (autocomplete).

**Response:**

```json
{
  "tickers": [
    { "symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology" }
  ]
}
```

---

### Async Jobs

#### `POST /api/jobs/optimize`

Submit async optimization. Returns `job_id`.

**Request:**

```json
{
  "payload": { /* optimize request */ },
  "webhook_url": "https://your-server/callback"
}
```

#### `POST /api/jobs/backtest`

Submit async backtest. Returns `job_id`.

#### `GET /api/jobs/<job_id>`

Poll job status. Returns `status` (pending/running/completed/failed) and result when completed.

---

### Lab Runs (durable experiment registry)

Lab runs persist experiment specs and results to SQLite so users can leave the Portfolio Lab and return later to view a report.

#### `POST /api/runs`

Create a durable lab run. Enqueues async optimization and returns immediately.

**Request:**

```json
{
  "payload": {
    "returns": [...],
    "covariance": [[...]],
    "asset_names": ["AAPL", "MSFT"],
    "objective": "hybrid",
    "weight_min": 0.005,
    "weight_max": 0.30,
    "seed": 42,
    "data_mode": "synthetic",
    "regime": "normal"
  }
}
```

**Response (202):**

```json
{ "run_id": "<uuid>", "status": "queued" }
```

#### `GET /api/runs`

List recent lab runs for the authenticated tenant.

| Query param | Default | Notes |
|-------------|---------|-------|
| `limit` | 20 | Max 100. |

**Response:** `{ "runs": [...], "count": N }`

#### `GET /api/runs/<id>`

Fetch a single run. Returns spec, status, result (when completed), and error (when failed). 403 if the run belongs to a different tenant.

**Response:**

```json
{
  "id": "<uuid>",
  "tenant_id": "default",
  "status": "completed",
  "execution_kind": "async_optimize",
  "spec": { "objective": "hybrid", "weight_min": 0.005, "..." : "..." },
  "result": { "sharpe_ratio": 1.23, "weights": [...], "holdings": [...] },
  "error": null,
  "created_at": "2026-03-24T...",
  "started_at": "...",
  "finished_at": "..."
}
```

---

### Metrics

#### `GET /metrics`

Prometheus metrics (request counts, latencies, optimization duration).

---

## Error Responses

Errors return:

```json
{
  "error": {
    "code": "ERROR",
    "message": "Human-readable message"
  }
}
```

HTTP status codes: 400 (validation), 401 (unauthorized), 429 (rate limit), 500 (server error).

---

*Last updated: 2026-02*
