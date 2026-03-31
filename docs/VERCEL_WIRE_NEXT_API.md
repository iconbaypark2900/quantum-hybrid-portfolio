# Wire Next (Project B) → Flask API (Project A) on Vercel

Follow in order. Use **two Vercel projects** from the same repo: **API at repo root** and **Next with Root Directory `web/`**.

If the dashboard shows **API STATUS: Unknown**, red errors like **“The page could not be found”**, or **404** on `/api/health` in DevTools, the **Next** project is not forwarding `/api/*` to a live API (usually **missing `API_PROXY_TARGET`** on Vercel for Option 2).

---

## 0. URLs

After first successful deploys, note:

| Project | Example hostname |
|--------|-------------------|
| **A — API** | `https://<your-api>.vercel.app` |
| **B — Next (`web/`)** | `https://<your-web>.vercel.app` |

Use **HTTPS**, **no trailing slash** on base URLs.

---

## 1. Project A (Flask API) — env

In **Project A → Settings → Environment Variables** (at least **Production**):

| Name | Value |
|------|--------|
| `API_KEY` | Strong shared secret (same value you use as `NEXT_PUBLIC_API_KEY` on B) |
| `TIINGO_API_KEY` | Optional; omit or set `DATA_PROVIDER=yfinance` for smoke-only |
| `CORS_ORIGINS` | **Option 1 only** — include `https://<your-web>.vercel.app` (and preview URLs if needed). **Option 2 — omit or leave default** for browser→API (server-side proxy). |
| `DASHBOARD_PUBLIC_URL` | Optional — `https://<your-web>.vercel.app` for `GET /` JSON on the API |

Redeploy **Project A** after changes.

**Smoke test:**

```bash
curl -sS "https://<your-api>.vercel.app/api/health"
# If API_KEY is required:
curl -sS -H "X-API-Key: $API_KEY" "https://<your-api>.vercel.app/api/health"
```

---

## 2. Project B (Next `web/`) — pick Option 2 **or** Option 1

### Option 2 (recommended): same-origin `/api/*` → Next rewrites to API

Browser calls **`https://<your-web>.vercel.app/api/...`** only. Next proxies to Flask (**no CORS** needed for browser→API).

In **Project B → Settings → Environment Variables**:

| Name | Value |
|------|--------|
| `API_PROXY_TARGET` | `https://<your-api>.vercel.app` |
| `NEXT_PUBLIC_API_KEY` | **Same string as** `API_KEY` on Project A |
| `NEXT_PUBLIC_API_URL` | **Leave unset** or empty (do not set to the Next URL) |

Do **not** leave `API_PROXY_TARGET` as `http://127.0.0.1:5000` on Vercel — that is for **local** dev only.

Redeploy **Project B** after saving (new build picks up `API_PROXY_TARGET` for `next.config.ts` rewrites).

### Option 1: browser calls API directly

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://<your-api>.vercel.app` |
| `NEXT_PUBLIC_API_KEY` | Same as `API_KEY` on A |

On **Project A**, set **`CORS_ORIGINS`** to include `https://<your-web>.vercel.app`. Redeploy both if needed.

---

## 3. Verify from the browser

1. Open **`https://<your-web>.vercel.app`** (dashboard).
2. DevTools → **Network** → reload → **`/api/health`** should be **200** JSON (not HTML 404).
3. Quantum / Settings pages should show API **Online** when health is healthy.

---

## Fix mistaken `YOUR_KEY` / `YOUR_API_BASE` or one Vercel project for both apps

If you ran `printf` with the **literal** strings `YOUR_KEY` or `YOUR_API_BASE`, Vercel stored those words — **delete** those env entries and set real values.

**Two projects:** `API_KEY` belongs on the **API** Vercel project; `API_PROXY_TARGET` and `NEXT_PUBLIC_API_KEY` belong on the **Next** (`web/`) project. If **`vercel link`** was only run in one folder, root and `web/` may share one project — run **`vercel link`** again from **`web/`** and attach the **dashboard** project (different name than the API).

**Scripted recovery (repo root):**

```bash
chmod +x scripts/vercel-option2-env.sh
# Optional: remove wrong names (confirm prompts)
./scripts/vercel-option2-env.sh --remove-wrong-env production
# Dry-run: prints a fresh key + commands
./scripts/vercel-option2-env.sh 'https://<your-api>.vercel.app' --dry-run
# Apply (requires distinct projectIds in .vercel for root vs web/)
./scripts/vercel-option2-env.sh 'https://<your-api>.vercel.app' --apply
```

The script **rejects** placeholder-looking values and **refuses** if repo root and `web/` resolve to the **same** `projectId`.

**Same `projectId` error on `--apply`:** `web/` was linked to the **API** project. Run **`./scripts/vercel-option2-env.sh --reset-web-link`**, then **`cd web && npx vercel link`** and choose the **Next** dashboard project (e.g. `quantum-hybrid-portfolio-5ch5`), not `quantum-hybrid-portfolio`. Then **`--apply`** again.

---

## Related

- [VERCEL_TWO_PROJECTS.md](VERCEL_TWO_PROJECTS.md) — full architecture
- [VERCEL_CLI.md](VERCEL_CLI.md) — `vercel env add`, deploy scripts
