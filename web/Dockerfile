# Fly.io Dockerfile for the Next.js web app (web/).
# Uses Next.js standalone output for a minimal runtime image.
# Deploy from repo root: fly deploy --config web/fly.toml
# Or from web/: fly deploy

# ─── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:20-slim AS builder
WORKDIR /app

# NEXT_PUBLIC_* is inlined at `npm run build`. API_PROXY_TARGET is read at runtime
# by `src/app/api/[[...path]]/route.ts` (Fly secrets / container env — not required here).
ARG NEXT_PUBLIC_API_KEY=
ENV NEXT_PUBLIC_API_KEY=$NEXT_PUBLIC_API_KEY
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# node:20-slim reserves UID 1000 for the built-in `node` user.
RUN useradd -m -u 1001 nextjs
USER nextjs

# Standalone output includes its own node_modules copy.
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./

# Static assets and public dir must be copied alongside standalone.
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

# Fly maps external 443 → internal 3000 via http_service in web/fly.toml.
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
