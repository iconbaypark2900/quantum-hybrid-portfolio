# Vercel: terminal + IDE workflow

Do **one-time** linking and env setup from the shell; then use the helper scripts or **`npx vercel`** for deploys. The Vercel dashboard is optional for routine work.

**Requirements:** Node/npm (for `npx vercel`), and a Vercel account (`vercel login`).

---

## 1. Install / run the CLI

No global install required:

```bash
npx vercel@latest --version
```

Optional global install: `npm i -g vercel`.

---

## 2. Log in (once per machine)

```bash
npx vercel@latest login
```

---

## 3. Link two projects (once per clone / machine)

Each directory gets its **own** Vercel project (`.vercel/` is gitignored).

**Project A — API (repo root)**

```bash
cd /path/to/quantum-hybrid-portfolio
npx vercel@latest link
```

- Scope: your team
- Link to existing project **or** create a new one (e.g. `quantum-hybrid-portfolio-api`)

**Project B — Next (`web/`)**

```bash
cd web
npx vercel@latest link
```

- Create/link a **different** project (e.g. `quantum-hybrid-portfolio-web`)

Deploying from `web/` means Vercel uses **`web/`** as the app root—no dashboard “Root Directory” setting required.

---

## 4. Environment variables (CLI)

Set variables **from the same directory** you linked (`api` vs `web`).

**API (repo root)**

```bash
cd /path/to/quantum-hybrid-portfolio
npx vercel@latest env add API_KEY production
npx vercel@latest env add CORS_ORIGINS production
npx vercel@latest env add CORS_ORIGINS preview
```

**Web (`web/`)** — pick **one** pattern (see [VERCEL_TWO_PROJECTS.md](VERCEL_TWO_PROJECTS.md)):

*Option 1 — direct API (needs `CORS_ORIGINS` on the API project):*

```bash
cd web
npx vercel@latest env add NEXT_PUBLIC_API_URL production
npx vercel@latest env add NEXT_PUBLIC_API_KEY production
```

*Option 2 — proxy via Next (`NEXT_PUBLIC_API_URL` empty, set `API_PROXY_TARGET` to the API base URL):*

```bash
cd web
npx vercel@latest env add API_PROXY_TARGET production
npx vercel@latest env add NEXT_PUBLIC_API_KEY production
```

**List / pull**

```bash
npx vercel@latest env ls
npx vercel@latest env pull .env.local
```

**Caution:** `env pull` **overwrites** `.env.local`. Keys that exist only locally but not in Vercel (e.g. `NEXT_PUBLIC_*`) can be **removed**. Restore them from [web/.env.example](../web/.env.example) or re-add with `vercel env add`.

For Option 1, `CORS_ORIGINS` on the API must list the dashboard origin(s). After changing API env, redeploy the API.

---

## 5. Deploy (production)

From repo root:

```bash
chmod +x scripts/vercel-deploy-api.sh scripts/vercel-deploy-web.sh
./scripts/vercel-deploy-api.sh
./scripts/vercel-deploy-web.sh
```

Or manually:

```bash
cd /path/to/quantum-hybrid-portfolio && npx vercel@latest deploy --prod
cd web && npx vercel@latest deploy --prod
```

**Override CLI binary** (e.g. global `vercel`):

```bash
VERCEL_BIN=vercel ./scripts/vercel-deploy-api.sh
```

---

## 6. Git → automatic builds

Connect the GitHub repo to **each** Vercel project (Settings → Git in the dashboard, or Vercel API). Pushes to `main` trigger builds without the CLI.

---

## 7. IDE (VS Code / Cursor)

Use **Terminal → Run Task** → *Vercel: Deploy API (prod)*, *Vercel: Deploy Web (prod)*, or *Vercel: Login* (see `.vscode/tasks.json`).

---

## Related

- [VERCEL_TWO_PROJECTS.md](VERCEL_TWO_PROJECTS.md) — architecture and env meanings
- [DEPLOYMENT.md](DEPLOYMENT.md) — general deployment notes
