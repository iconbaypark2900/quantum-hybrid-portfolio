# Deployment guide

This document describes how to run and deploy the Quantum Ledger stack: the Flask API and the Next.js dashboard.

---

## Stack overview

| Component | Path | Default port |
|-----------|------|-------------|
| Flask API | `api/app.py` (`python -m api`) | 5000 |
| Next.js dashboard (primary) | `web/` | 3042 |
| CRA dashboard (legacy) | `frontend/` | 3000 |

---

## Required environment variables

Create `.env` by copying `.env.example` and filling in values.

| Variable | Required | Purpose |
|----------|----------|---------|
| `API_KEY` | Yes | Shared secret for `X-API-Key` header on all API calls |
| `TIINGO_API_KEY` | Yes (for live data) | Market data provider — free at https://api.tiingo.com |
| `DATA_PROVIDER` | No | `tiingo` (default when key set), `yfinance` (legacy fallback) |
| `NEXT_PUBLIC_API_KEY` | Yes (Next.js) | Same value as `API_KEY`; exposed to browser via `NEXT_PUBLIC_` prefix |
| `NEXT_PUBLIC_API_URL` | No | Full base URL to Flask API from browser. If empty, Next.js rewrites `/api/*` to `API_PROXY_TARGET` server-side (default `http://127.0.0.1:5000`) |
| `API_PROXY_TARGET` | No | Server-side override for `web/next.config.ts` rewrite target (default `http://127.0.0.1:5000`) |
| `NEXT_WEB_PORT` | No | Port for `next dev` (default 3042) |

---

## Local development (two terminals)

**Terminal 1 — Flask API:**

```bash
source .venv/bin/activate
python -m api
# API available at http://localhost:5000
```

**Terminal 2 — Next.js dashboard:**

```bash
cd web && npm install   # first run only
cd web && npm run dev
# Dashboard at http://localhost:3042
```

Or use the convenience script:

```bash
bash scripts/run-next-web.sh
```

---

## Production build

**Flask API** — no build step; run with a production WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

**Next.js dashboard:**

```bash
cd web
npm ci
npm run build
npm start   # or serve .next/ with any Node.js host
```

---

## Same-host deployment (recommended)

Run Next.js and Flask on the same host. Configure `API_PROXY_TARGET` so the Next.js server rewrites `/api/*` requests to the Flask port:

```
API_PROXY_TARGET=http://127.0.0.1:5000
NEXT_PUBLIC_API_URL=           # leave empty so rewrites apply
```

This avoids CORS issues entirely — the browser only talks to the Next.js origin.

---

## Split-host deployment

If Flask and Next.js are on separate hosts, set:

```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
CORS_ORIGINS=https://dashboard.yourdomain.com
```

Flask's `CORS_ORIGINS` (default `http://localhost:3000`) must include the Next.js origin.

---

## Vercel (two projects: API + Next.js)

Typical setup: **Project A** = Python/Flask at repo root (`pyproject.toml`); **Project B** = Next.js with **Root Directory** `web`. Set **`NEXT_PUBLIC_API_URL`** on B to A’s URL and **`CORS_ORIGINS`** on A to B’s origin.

Step-by-step: **[docs/VERCEL_TWO_PROJECTS.md](VERCEL_TWO_PROJECTS.md)**. CLI / terminal: **[docs/VERCEL_CLI.md](VERCEL_CLI.md)**.

---

## Rollback procedure

| Scenario | Action |
|----------|--------|
| Next.js broken in prod | Revert deploy; serve CRA `frontend/build/` statically as a fallback |
| API contract change | Bump version in `docs/openapi.yaml`; coordinate with Next.js `web/src/lib/api.ts` |
| Bad Tiingo key | Set `DATA_PROVIDER=yfinance` temporarily; restore Tiingo key and revert |

---

## Health check

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5000/api/health
```

Expected: `{"data": {"checks": {"api": "ok", ...}}, ...}`

---

## Related

- [docs/GETTING_STARTED.md](GETTING_STARTED.md) — install steps
- [docs/DATA_PIPELINE.md](DATA_PIPELINE.md) — scripts and DB layout
- [docs/VERCEL_TWO_PROJECTS.md](VERCEL_TWO_PROJECTS.md) — Vercel API + Next.js two-project setup
- [docs/VERCEL_CLI.md](VERCEL_CLI.md) — Vercel CLI, deploy scripts, IDE tasks
- [AGENTS.md](../AGENTS.md) — port, env, and proxy facts for agents
