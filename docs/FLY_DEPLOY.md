# Fly.io two-app deploy (Flask API + Next `web/`)

This project deploys as **two separate Fly apps** that communicate over Fly's private network:

- **App A** — Flask API (`api.app`), port 5000, built from `Dockerfile.fly` at repo root.
- **App B** — Next.js web UI (`web/`), port 3000, built from `web/Dockerfile`.

The browser only talks to the **Next** hostname. `web/next.config.ts` rewrites `/api/*` to the Flask API via `API_PROXY_TARGET`, so no browser-level CORS to Flask is needed.

```
Browser  ──HTTPS──►  App B (Next, fly.dev)  ──private .internal──►  App A (Flask, .internal:5000)
```

---

## 0. Prerequisites

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Authenticate
fly auth login
```

---

## 1. Create the two Fly apps

```bash
fly apps create <your-api-app-name>    # e.g. quantum-api
fly apps create <your-web-app-name>    # e.g. quantum-web
```

Note both names — they must match `app = '...'` in `fly.toml` and `web/fly.toml`.

---

## 2. App A — Flask API

### 2a. Update `fly.toml`

Edit `fly.toml` at repo root and set:

```toml
app = '<your-api-app-name>'
primary_region = 'ord'   # change to region closest to your users
```

### 2b. Set secrets

```bash
fly secrets set \
  API_KEY=<strong-random-secret> \
  TIINGO_API_KEY=<your-tiingo-key> \
  --app <your-api-app-name>
```

Optional IBM Quantum credentials (needed for VQE/QAOA hardware paths):

```bash
fly secrets set \
  IBM_QUANTUM_TOKEN=<your-ibm-token> \
  --app <your-api-app-name>
```

Optional SQLite persistence (uncomment `[[mounts]]` in `fly.toml` first, then create the volume):

```bash
fly volumes create quantum_data --region ord --size 1 --app <your-api-app-name>
fly secrets set API_DB_PATH=/data/api.sqlite3 --app <your-api-app-name>
```

### 2c. Deploy

```bash
# From repo root
fly deploy --config fly.toml
```

### 2d. Smoke test

```bash
curl -sS https://<your-api-app-name>.fly.dev/api/health
# Expected: {"status": "healthy", ...}
```

---

## 3. App B — Next.js web

### 3a. Update `web/fly.toml`

Edit `web/fly.toml` and set:

```toml
app = '<your-web-app-name>'
primary_region = 'ord'   # match App A's region so .internal traffic is fast
```

### 3b. Set secrets

`API_PROXY_TARGET` must point to the Flask API using Fly's **private network DNS**. The pattern is `http://<api-app-name>.internal:5000` (no trailing slash).

```bash
fly secrets set \
  API_PROXY_TARGET=http://<your-api-app-name>.internal:5000 \
  NEXT_PUBLIC_API_KEY=<same-value-as-API_KEY-above> \
  --app <your-web-app-name>
```

`NEXT_PUBLIC_API_URL` should be **left unset** (or empty). The rewrites in `web/next.config.ts` handle routing — the browser never calls Flask directly.

### 3c. Deploy

```bash
# From web/
cd web
fly deploy
```

Or from repo root:

```bash
fly deploy --config web/fly.toml
```

### 3d. Verify end-to-end

1. Open `https://<your-web-app-name>.fly.dev` in a browser.
2. Open DevTools → Network → reload.
3. `/api/health` should return **200** JSON.
4. The Settings page should show API **Online**.

---

## Environment variable reference

### App A (Flask API)

| Variable | Required | Notes |
|----------|----------|-------|
| `API_KEY` | Yes | Shared secret; must match `NEXT_PUBLIC_API_KEY` on App B |
| `TIINGO_API_KEY` | Recommended | Set `DATA_PROVIDER=tiingo` when present |
| `IBM_QUANTUM_TOKEN` | Optional | Enables VQE/QAOA hardware paths |
| `API_DB_PATH` | Optional | Default `/tmp/api.sqlite3`; set to `/data/api.sqlite3` with a volume for persistence |
| `CORS_ORIGINS` | Optional | Only needed if browser calls API directly (not via Next proxy) |

### App B (Next.js web)

| Variable | Required | Notes |
|----------|----------|-------|
| `API_PROXY_TARGET` | Yes | `http://<api-app>.internal:5000` — Next server → Flask via private network |
| `NEXT_PUBLIC_API_KEY` | Yes | Same value as `API_KEY` on App A |
| `NEXT_PUBLIC_API_URL` | No | Leave unset when using the `/api` proxy (Option 2) |

---

## Local Docker smoke test (before deploying)

```bash
# Build and run API locally
docker build -f Dockerfile.fly -t quantum-api-fly .
docker run --rm -p 5000:5000 -e API_KEY=dev quantum-api-fly
curl http://localhost:5000/api/health

# Build and run Next locally (assumes API is running on 5000)
docker build -f web/Dockerfile -t quantum-web-fly web/
docker run --rm -p 3000:3000 \
  -e API_PROXY_TARGET=http://host.docker.internal:5000 \
  -e NEXT_PUBLIC_API_KEY=dev \
  quantum-web-fly
# Then open http://localhost:3000 and check /api/health in DevTools
```

---

## Updating after code changes

```bash
# API
fly deploy --config fly.toml

# Web
fly deploy --config web/fly.toml   # or: cd web && fly deploy
```

Both apps can be deployed independently. The private `.internal` DNS is stable as long as the app name does not change.

---

## Troubleshooting

**Fly Doctor: “App is not listening on internal_port 7860” or 502 Bad Gateway**

The **API** app (`Dockerfile.fly`) listens on **`PORT`**, default **5000**. `fly.toml` must use **`internal_port = 5000`**.

- **7860** is only for **Hugging Face** / the root `Dockerfile` + `serve_hf.py`, not for Fly’s API deploy.
- If the dashboard or an old `fly launch` set **internal_port = 7860**, change it to **5000** (or edit `fly.toml` and run `fly deploy`).
- After changing port, redeploy so Fly’s proxy and `PORT` match the container.

**`/api/health` returns 404 or HTML from the Next app**
→ `API_PROXY_TARGET` is missing or wrong on App B. Check with:

```bash
fly secrets list --app <your-web-app-name>
```

**API returns 500 on IBM paths**
→ `IBM_QUANTUM_TOKEN` is not set or token has expired. Re-set the secret and redeploy.

**OOM on API machine**
→ Raise memory in `fly.toml`:

```toml
[[vm]]
  memory = '2gb'
```

Then redeploy. The heavy numpy/qiskit cold start needs at least 1 GB; 2 GB if you use `--preload` with multiple workers.
