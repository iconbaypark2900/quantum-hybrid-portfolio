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

---

## Endpoints

### Health

#### `GET /api/health`

Returns API health and version.

**Response:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-15T12:00:00Z"
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
