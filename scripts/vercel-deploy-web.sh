#!/usr/bin/env bash
# Deploy the Next.js dashboard (web/) to Vercel (production).
# Prerequisite: run `npx vercel link` once inside web/ and connect the dashboard project.
#
# Usage:
#   ./scripts/vercel-deploy-web.sh
#   VERCEL_BIN=vercel ./scripts/vercel-deploy-web.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/web"
cd "$WEB"

VERCEL_BIN="${VERCEL_BIN:-npx --yes vercel@latest}"

if [[ ! -f "$WEB/package.json" ]]; then
  echo "error: web/package.json not found. Install deps: cd web && npm install" >&2
  exit 1
fi

echo "Deploying Next.js from: $WEB"
exec $VERCEL_BIN deploy --prod "$@"
