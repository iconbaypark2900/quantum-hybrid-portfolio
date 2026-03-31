# Vercel: API + Next.js (two projects)

Use **two Vercel projects** from the same GitHub repo: one for the **Flask API** (Python) and one for the **Next.js dashboard** (`web/`). The browser talks to the API either **cross-origin** (set `NEXT_PUBLIC_API_URL` + Flask `CORS_ORIGINS`) or you can keep split deploy and always use the direct API URL from the client.

---

## Project A — Python API only

| Setting | Value |
|--------|--------|
| **Root Directory** | Repository root (`.`) |
| **Framework** | Vercel Python / auto-detect from `pyproject.toml` |
| **Install** | Uses `pyproject.toml` + `requirements-vercel.txt` (slim deps) |

**Environment variables (Production / Preview as needed)**

| Variable | Purpose |
|----------|---------|
| `API_KEY` | Shared secret; clients send `X-API-Key` |
| `TIINGO_API_KEY` | Live market data (optional; can use `DATA_PROVIDER=yfinance` for smoke) |
| `API_DB_PATH` | Optional; serverless defaults to `/tmp/api.sqlite3` when `VERCEL` / `VERCEL_ENV` apply (see `api/app.py`) |
| `CORS_ORIGINS` | **Required** if the dashboard is on a **different origin** than this API. Comma-separated list of allowed UI origins, e.g. `https://your-dashboard.vercel.app` |

**Smoke test**

```bash
curl -sS "https://<project-a>.vercel.app/api/health"
```

Use `-H "X-API-Key: $API_KEY"` if your deployment requires it.

---

## Project B — Next.js (`web/`)

| Setting | Value |
|--------|--------|
| **Root Directory** | `web` |
| **Framework** | Next.js (auto) |

**Environment variables**

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | **Full base URL of Project A**, no trailing slash, e.g. `https://<project-a>.vercel.app`. The client (`web/src/lib/api.ts`) uses this as Axios `baseURL`. |
| `NEXT_PUBLIC_API_KEY` | Same value as Project A’s `API_KEY` (embedded in browser bundle). |

With `NEXT_PUBLIC_API_URL` set, the browser calls the API **directly** on Project A. **`API_PROXY_TARGET`** rewrites in `next.config.ts` are mainly for **local dev** when `NEXT_PUBLIC_API_URL` is empty.

**Do not** set `NEXT_PUBLIC_API_URL` to the Project B URL unless you intentionally proxy; for split deployment, it must be **Project A’s** URL.

---

## CORS checklist

1. Deploy Project A; copy its production URL (e.g. `https://quantum-api.vercel.app`).
2. Deploy Project B with `NEXT_PUBLIC_API_URL` = that URL.
3. On **Project A**, set `CORS_ORIGINS` to **Project B’s** origin(s), e.g.  
   `https://quantum-dashboard.vercel.app`  
   Include preview URLs if you test previews:  
   `https://quantum-dashboard-xxx-team.vercel.app` (or use Preview env vars in Vercel per environment).

Flask’s `CORS_ORIGINS` is read at startup (`api/app.py`). After changing it, redeploy Project A.

---

## Optional: same-origin (advanced)

To avoid CORS entirely you would need the Next app to proxy `/api/*` to Project A **on the server** (Next rewrites to an absolute URL). That requires Project B’s server to reach Project A (possible on Vercel) and is a different wiring than `NEXT_PUBLIC_API_URL` pointing at A. The **simple split-host** pattern is: **`NEXT_PUBLIC_API_URL` + `CORS_ORIGINS`**.

---

## Terminal / CLI (no dashboard)

See **[docs/VERCEL_CLI.md](VERCEL_CLI.md)** — `vercel link`, `vercel env`, deploy scripts (`scripts/vercel-deploy-*.sh`), and VS Code tasks.

---

## Related

- [DEPLOYMENT.md](DEPLOYMENT.md) — general env and split-host notes
- [VERCEL_CLI.md](VERCEL_CLI.md) — CLI + IDE workflow
- [AGENTS.md](../AGENTS.md) — local ports and proxy behavior
